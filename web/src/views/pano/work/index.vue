<template>
  <div class="h-screen w-full flex overflow-hidden bg-gray-900">
    <div class="relative h-full w-2/3 border-r border-gray-700">
      <div ref="psvContainerRef" class="h-full w-full cursor-crosshair"></div>

      <div
        class="pointer-events-none absolute left-4 top-4 rounded bg-black/60 px-4 py-2 text-white"
      >
        左键拖拽旋转视角 | 滚轮缩放 | 点击物体获取切片
      </div>
    </div>

    <div class="h-full w-1/3 flex flex-col bg-white">
      <div class="border-b p-4">
        <h3 class="text-lg font-bold">2D 无畸变透视工作台</h3>
        <p class="mt-1 text-xs text-gray-500">请在左侧点击物体，获取正交切片进行标注</p>
      </div>

      <div class="flex flex-col flex-1 gap-6 overflow-y-auto p-4">
        <div
          class="relative aspect-square w-full flex items-center justify-center overflow-hidden border border-gray-300 rounded border-dashed bg-gray-100"
        >
          <img
            v-if="perspectiveData.base64"
            :src="perspectiveData.base64"
            class="h-full w-full object-contain"
            alt="透视切片"
            draggable="false"
          />
          <div v-else class="text-gray-400">等待切片生成...</div>

          <div
            v-if="perspectiveData.base64 && isDrawing"
            class="pointer-events-none absolute border-2 border-green-500 bg-green-500/20"
            :style="boxStyle"
          >
            <div
              class="absolute left-1/2 top-1/2 h-1 w-1 rounded-full bg-red-500 -translate-x-1/2 -translate-y-1/2"
            ></div>
          </div>
        </div>

        <div v-if="perspectiveData.base64" class="flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <span class="font-bold">开启框选</span>
            <n-switch v-model:value="isDrawing" />
          </div>

          <template v-if="isDrawing">
            <div>
              <div class="mb-1 text-xs text-gray-500">中心点 X (px)</div>
              <n-slider v-model:value="boxParams.cx" :min="0" :max="512" />
            </div>
            <div>
              <div class="mb-1 text-xs text-gray-500">中心点 Y (px)</div>
              <n-slider v-model:value="boxParams.cy" :min="0" :max="512" />
            </div>
            <div>
              <div class="mb-1 text-xs text-gray-500">宽度 Width (px)</div>
              <n-slider v-model:value="boxParams.w" :min="10" :max="400" />
            </div>
            <div>
              <div class="mb-1 text-xs text-gray-500">高度 Height (px)</div>
              <n-slider v-model:value="boxParams.h" :min="10" :max="400" />
            </div>
            <div>
              <div class="mb-1 flex justify-between text-xs text-gray-500">
                <span>旋转角度 (Gamma)</span>
                <span>{{ boxParams.angle }}°</span>
              </div>
              <n-slider v-model:value="boxParams.angle" :min="-90" :max="90" :step="1" />
            </div>

            <n-button type="primary" class="mt-4" :loading="isSaving" @click="submitAnnotation">
              保存 5-DOF 标注
            </n-button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
// 假设你项目里有封装好的 axios 实例，请按需引入
// import request from '@/utils/request'

// 🌟 PSV 核心与插件
import { Viewer } from '@photo-sphere-viewer/core'
import { MarkersPlugin } from '@photo-sphere-viewer/markers-plugin'
import '@photo-sphere-viewer/core/index.css'
import '@photo-sphere-viewer/markers-plugin/index.css'
import imageApi from '@/api/image'
// import projectApi from '@/api/project'

const route = useRoute()

// DOM 引用
const psvContainerRef = ref(null)

// 🌟 引擎实例 (必须放在普通变量里，绝不能用 ref 包装，否则会导致 WebGL 性能崩溃！)
let viewer = null
let markersPlugin = null

// 全局状态
const imageId = route.query.imageId || 1
const imageUrl =
  route.query.url || 'http://127.0.0.1:9999/static/uploads/14258c9caa6b4f908584e5a37b75eac7.jpg'

// 透视切片数据 (由后端 cv2.remap 返回)
const perspectiveData = ref({
  base64: '',
  theta: 0,
  phi: 0,
  fov: 90,
})

// 画框状态
const isDrawing = ref(false)
const isSaving = ref(false)

// 2D 旋转框参数 (默认在画布中央 512x512)
const boxParams = ref({
  cx: 256,
  cy: 256,
  w: 100,
  h: 100,
  angle: 0,
})

// 计算 CSS 样式：渲染那个绿色的带旋转的框
const boxStyle = computed(() => {
  // 我们滑块控制的是中心点 cx/cy，CSS left/top 需要的是左上角坐标
  const left = boxParams.value.cx - boxParams.value.w / 2
  const top = boxParams.value.cy - boxParams.value.h / 2
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${boxParams.value.w}px`,
    height: `${boxParams.value.h}px`,
    transform: `rotate(${boxParams.value.angle}deg)`,
    transformOrigin: 'center center', // 绕着中心点旋转
  }
})

// ==========================================
// 1. 初始化 3D WebGL 全景查看器
// ==========================================
const initPanoViewer = () => {
  if (!psvContainerRef.value) return

  viewer = new Viewer({
    container: psvContainerRef.value,
    panorama: imageUrl,
    navbar: ['zoom', 'fullscreen'],
    defaultZoomLvl: 30, // 初始视角稍微拉近一点
    plugins: [[MarkersPlugin, {}]],
  })

  markersPlugin = viewer.getPlugin(MarkersPlugin)

  // 🎯 核心魔法：监听 3D 鼠标点击，直接获取精确的原图像素坐标 (textureX/Y)
  viewer.addEventListener('click', ({ data }) => {
    const u = data.textureX
    const v = data.textureY
    console.log(
      `🎯 [PSV] 点击球面经纬度 (rad): Yaw=${data.yaw.toFixed(4)}, Pitch=${data.pitch.toFixed(4)}`
    )
    console.log(`🎯 [PSV] 对应原图像素坐标: u=${u.toFixed(2)}, v=${v.toFixed(2)}`)

    // 触发后端切图
    fetchPerspectiveCrop(u, v)
  })
}

// ==========================================
// 2. 请求后端：生成 2D 无畸变局部透视图
// ==========================================
const fetchPerspectiveCrop = async (u, v) => {
  try {
    // 【请将此处的 fetch 替换为你真实的 axios 请求】
    /*
    const res = await request.post('/api/v1/image/perspective', {
      image_id: Number(imageId),
      u: Number(u),
      v: Number(v),
      fov: 90.0
    })
    // 假设响应格式是之前后端的返回值
    perspectiveData.value.base64 = res.data.image_base64
    perspectiveData.value.theta = res.data.center_theta
    perspectiveData.value.phi = res.data.center_phi
    perspectiveData.value.fov = res.data.fov
    */
    const data = await response.json()
    perspectiveData.value = {
      base64: data.image_base64,
      theta: data.center_theta,
      phi: data.center_phi,
      fov: data.fov,
    }

    // 重置画框状态
    isDrawing.value = true
    boxParams.value = { cx: 256, cy: 256, w: 100, h: 100, angle: 0 }
  } catch (error) {
    console.error('切图失败:', error)
  }
}

// ==========================================
// 3. 提交标注：保存 5-DOF 参数，拿到点阵后渲染曲面
// ==========================================
const submitAnnotation = async () => {
  isSaving.value = true
  try {
    // 转换中心点格式为左上角格式 (适配后端之前写的 box_x, box_y 逻辑)
    const box_x = boxParams.value.cx - boxParams.value.w / 2
    const box_y = boxParams.value.cy - boxParams.value.h / 2

    const payload = {
      label_id: 1, // 写死测试
      crop_theta: perspectiveData.value.theta,
      crop_phi: perspectiveData.value.phi,
      crop_fov: perspectiveData.value.fov,
      box_x: box_x,
      box_y: box_y,
      box_w: boxParams.value.w,
      box_h: boxParams.value.h,
      box_angle: boxParams.value.angle, // 🌟 新增的旋转角度
    }

    console.log('🚀 [Frontend] 发送 5-DOF 逆向投影请求:', payload)

    // 【请将此处的 fetch 替换为你真实的 axios 请求】
    const response = await fetch(`http://127.0.0.1:9999/api/v1/image/${imageId}/annotation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const result = await response.json()
    console.log('✅ [Backend] 收到逆向计算结果与多边形点阵:', result)

    // 🌟 这里是阶段二预留口：将 result.boundary_points 传给 PSV 渲染出完美曲面多边形！
    // drawPolygonOnSphere(result.id, result.boundary_points)

    alert('保存成功！请查看 F12 Console 中的点阵数据！')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    isSaving.value = false
  }
}

// 生命周期
onMounted(() => {
  // 留一点时间让外层 DOM 渲染完成，再挂载 WebGL
  setTimeout(() => {
    initPanoViewer()
  }, 100)
})

onBeforeUnmount(() => {
  if (viewer) {
    viewer.destroy() // 必须销毁，否则严重内存泄漏
  }
})
</script>

<style scoped>
/* 隐藏原生滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-thumb {
  background-color: #888;
  border-radius: 4px;
}
</style>
