import { request } from '@/utils'

export default {
  // 上传图片 (注意这里必须传 project_id)
  uploadImage: (data) =>
    request.post('/image/upload', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  // 获取项目下的图片列表
  getImages: (projectId) => request.get('/image/list', { params: { project_id: projectId } }),
  // 获取透视切片
  getPerspective: (data) => request.post('/image/crop', data),
  // 保存标注
  saveAnnotation: (imageId, data) => request.post(`/image/${imageId}/annotate`, data),
}
