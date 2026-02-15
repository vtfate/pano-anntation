<template>
  <div class="h-full flex flex-col p-4">
    <div class="mb-4 flex items-center justify-between rounded bg-white p-4 shadow-sm">
      <div class="flex items-center gap-4">
        <n-button circle size="small" @click="$router.back()">
          <template #icon><span class="text-lg">←</span></template>
        </n-button>
        <span class="text-lg font-bold">📁 项目控制台：{{ projectName }}</span>
      </div>
    </div>

    <n-card class="flex-1 shadow-sm" :bordered="false">
      <n-tabs type="line" size="large" animated>
        <n-tab-pane name="labels" tab="🏷️ 标签管理">
          <div class="mb-4">
            <n-button type="primary" @click="showLabelModal = true">新增标签</n-button>
          </div>

          <n-spin :show="loadingLabels">
            <n-table :bordered="false" :single-line="false">
              <thead>
                <tr>
                  <th>标签名称</th>
                  <th>展示颜色</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="label in labelList" :key="label.id">
                  <td class="font-bold">{{ label.name }}</td>
                  <td>
                    <n-tag :color="{ color: label.color, textColor: '#fff' }">
                      {{ label.color }}
                    </n-tag>
                  </td>
                  <td>{{ formatDate(label.created_at) }}</td>
                  <td>
                    <n-popconfirm @positive-click="handleDeleteLabel(label.id)">
                      <template #trigger>
                        <n-button size="small" type="error" ghost>删除</n-button>
                      </template>
                      确认删除该标签吗？(关联的标注也会被影响)
                    </n-popconfirm>
                  </td>
                </tr>
              </tbody>
            </n-table>
            <n-empty v-if="labelList.length === 0" description="暂无标签，请先添加" class="mt-10" />
          </n-spin>
        </n-tab-pane>

        <n-tab-pane name="images" tab="🖼️ 图片与标注">
          <div class="mb-4">
            <n-upload :custom-request="handleUploadImage" :show-file-list="false" accept="image/*">
              <n-button type="primary">上传全景图</n-button>
            </n-upload>
          </div>

          <n-spin :show="loadingImages">
            <n-grid x-gap="16" y-gap="16" cols="1 s:2 m:3 l:4" responsive="screen">
              <n-grid-item v-for="img in imageList" :key="img.id">
                <n-card hoverable class="cursor-pointer" @click="goWorkbench(img)">
                  <div class="relative h-48 overflow-hidden rounded">
                    <n-image
                      :src="fixUrl(img.url)"
                      object-fit="cover"
                      class="h-full w-full"
                      preview-disabled
                      lazy
                    />
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-black/50 font-bold text-white opacity-0 transition-opacity hover:opacity-100"
                    >
                      🚀 进入标注工作台
                    </div>
                  </div>
                  <div class="mt-2 truncate text-center font-bold" :title="img.filename">
                    {{ img.filename }}
                  </div>
                </n-card>
              </n-grid-item>
            </n-grid>

            <n-empty
              v-if="imageList.length === 0"
              description="该项目暂无图片，请上传"
              class="mt-10"
            />
          </n-spin>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <n-modal v-model:show="showLabelModal" preset="card" title="新增标签" class="w-[400px]">
      <n-form ref="labelFormRef" :model="labelForm" :rules="labelRules">
        <n-form-item label="标签名称 (如: chair)" path="name">
          <n-input v-model:value="labelForm.name" placeholder="请输入标签名" />
        </n-form-item>
        <n-form-item label="标签颜色" path="color">
          <n-color-picker v-model:value="labelForm.color" :show-alpha="false" />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" block :loading="submitLoading" @click="submitCreateLabel">
            确认添加
          </n-button>
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NTabs,
  NTabPane,
  NTable,
  NTag,
  NPopconfirm,
  NUpload,
  NGrid,
  NGridItem,
  NImage,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NColorPicker,
  NSpin,
  NEmpty,
  useMessage,
} from 'naive-ui'

// 引入我们的两个 API 模块
import projectApi from '@/api/project'
import imageApi from '@/api/image'

const route = useRoute()
const router = useRouter()
const message = useMessage()

// 路由传过来的参数
const projectId = ref(null)
const projectName = ref('')

// --- 标签相关状态 ---
const labelList = ref([])
const loadingLabels = ref(false)
const showLabelModal = ref(false)
const submitLoading = ref(false)
const labelFormRef = ref(null)
const labelForm = ref({ name: '', color: '#18A058' }) // 默认绿色
const labelRules = { name: { required: true, message: '请输入标签名', trigger: 'blur' } }

// --- 图片相关状态 ---
const imageList = ref([])
const loadingImages = ref(false)

// 格式化时间
const formatDate = (dateStr) => new Date(dateStr).toLocaleString()

// 修复图片相对路径
const fixUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `http://127.0.0.1:9999${url}` // 替换为你后端的实际端口 (9999)
}

// 初始化加载数据
onMounted(() => {
  const { id, name } = route.query
  if (id) {
    projectId.value = parseInt(id)
    projectName.value = name
    fetchLabels()
    fetchImages()
  } else {
    message.warning('缺少项目参数')
    router.back()
  }
})

// ================== 标签操作 ==================
const fetchLabels = async () => {
  loadingLabels.value = true
  try {
    const res = await projectApi.getLabels(projectId.value)
    labelList.value = res.data || res || []
  } catch (error) {
    console.error('获取标签失败', error)
  } finally {
    loadingLabels.value = false
  }
}

const submitCreateLabel = async () => {
  labelFormRef.value?.validate(async (errors) => {
    if (!errors) {
      submitLoading.value = true
      try {
        await projectApi.createLabel(projectId.value, labelForm.value)
        message.success('标签添加成功')
        showLabelModal.value = false
        labelForm.value = { name: '', color: '#18A058' }
        fetchLabels()
      } catch (error) {
        message.error('标签添加失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handleDeleteLabel = async (labelId) => {
  try {
    await projectApi.deleteLabel(labelId)
    message.success('删除成功')
    fetchLabels()
  } catch (error) {
    message.error('删除失败')
  }
}

// ================== 图片操作 ==================
const fetchImages = async () => {
  loadingImages.value = true
  try {
    const res = await imageApi.getImages(projectId.value)
    imageList.value = res.data || res || []
  } catch (error) {
    console.error('获取图片失败', error)
  } finally {
    loadingImages.value = false
  }
}

const handleUploadImage = async ({ file }) => {
  const formData = new FormData()
  // 核心：必须把 project_id 传给后端
  formData.append('project_id', projectId.value)
  formData.append('file', file.file)

  try {
    await imageApi.uploadImage(formData)
    message.success('图片上传成功')
    fetchImages() // 刷新图片列表
  } catch (error) {
    message.error('上传失败')
  }
}

// ================== 跳转标注工作台 ==================
const goWorkbench = (img) => {
  router.push({
    path: '/pano/work', // 我们最后要写的标注工作台
    query: {
      projectId: projectId.value, // 把项目ID传过去，为了拉取这个项目的标签
      imageId: img.id,
      url: fixUrl(img.url),
      name: img.filename,
    },
  })
}
</script>
