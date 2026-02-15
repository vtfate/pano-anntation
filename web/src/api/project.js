import { request } from '@/utils'

export default {
  // 获取所有项目
  getProjects: () => request.get('/project/list'),
  // 创建项目
  createProject: (data) => request.post('/project/create', data),
  // 获取项目的标签
  getLabels: (projectId) => request.get(`/project/${projectId}/labels`),
  // 创建标签
  createLabel: (projectId, data) => request.post(`/project/${projectId}/labels`, data),
  // 删除标签
  deleteLabel: (labelId) => request.delete(`/project/labels/${labelId}`),
}
