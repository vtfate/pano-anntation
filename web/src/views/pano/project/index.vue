<template>
  <div class="p-4">
    <n-card title="标注项目大厅" :bordered="false" class="shadow-sm">
      <template #header-extra>
        <n-button type="primary" @click="showModal = true"> 新建项目 </n-button>
      </template>

      <n-spin :show="loading">
        <n-grid x-gap="16" y-gap="16" cols="1 s:2 m:3 l:4" responsive="screen">
          <n-grid-item v-for="item in list" :key="item.id">
            <n-card hoverable class="h-full cursor-pointer" @click="goDetail(item)">
              <template #header>
                <span class="text-lg font-bold">📁 {{ item.name }}</span>
              </template>
              <p class="mt-2 text-gray-500" style="min-height: 40px">
                {{ item.description || '暂无描述' }}
              </p>
              <template #footer>
                <span class="text-xs text-gray-400"
                  >创建时间: {{ formatDate(item.created_at) }}</span
                >
              </template>
            </n-card>
          </n-grid-item>
        </n-grid>

        <n-empty v-if="list.length === 0" description="暂无项目，请先新建" class="mt-10" />
      </n-spin>
    </n-card>

    <n-modal v-model:show="showModal" preset="card" title="新建项目" class="w-[500px]">
      <n-form ref="formRef" :model="form" :rules="rules">
        <n-form-item label="项目名称" path="name">
          <n-input v-model:value="form.name" placeholder="请输入项目名称 (如: 会议室物体检测)" />
        </n-form-item>
        <n-form-item label="项目描述" path="description">
          <n-input v-model:value="form.description" type="textarea" placeholder="请输入描述" />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" block :loading="submitLoading" @click="submitCreate"
            >确认创建</n-button
          >
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NGrid,
  NGridItem,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSpin,
  NEmpty,
  useMessage,
} from 'naive-ui'
import api from '@/api/project'

const router = useRouter()
const message = useMessage()

// 列表数据
const list = ref([])
const loading = ref(false)

// 弹窗表单状态
const showModal = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const form = ref({ name: '', description: '' })
const rules = {
  name: { required: true, message: '请输入项目名称', trigger: 'blur' },
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString()
}

// 获取项目列表
const fetchList = async () => {
  loading.value = true
  try {
    const res = await api.getProjects()
    // 兼容可能的数据解构格式
    list.value = res.data || res || []
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 提交创建项目
const submitCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      submitLoading.value = true
      try {
        await api.createProject(form.value)
        message.success('创建成功')
        showModal.value = false
        form.value = { name: '', description: '' }
        fetchList() // 刷新列表
      } catch (error) {
        message.error('创建失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 跳转到项目详情 (我们下一步要写的页面)
const goDetail = (item) => {
  router.push({
    path: '/pano/project/detail',
    query: { id: item.id, name: item.name },
  })
}

onMounted(fetchList)
</script>
