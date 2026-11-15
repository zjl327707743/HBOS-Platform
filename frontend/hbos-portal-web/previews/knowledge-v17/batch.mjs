export async function getManagedSpaces(){return {can_manage_spaces:false,spaces:[{space_id:'MOCK_SPACE',title:'合成空间',department:'production'}]}}
export async function getManagedTemplates(){return {templates:[]}}
const pipelineItems=[
 {batch_id:'MOCK_BATCH',document_id:'DOC_SYNTHETIC_0',version_id:'V01',title:'培养箱使用与日常检查指南',filename:'培养箱使用与日常检查指南.pdf',relative_path:'生产/培养箱使用与日常检查指南.pdf',queue:'NORMAL',status:'READY_FOR_ADOPTION',reasons:[],resume_safe:false,validation_retry:false},
 {batch_id:'MOCK_BATCH',document_id:'DOC_SYNTHETIC_1',version_id:'V02',title:'岗位安全培训资料索引',filename:'岗位安全培训资料索引.pdf',relative_path:'生产/岗位安全培训资料索引.pdf',queue:'COMPLEX',status:'REPAIR_REQUIRED',reasons:['SOURCE_TEXT_OR_NUMBER_COVERAGE_REPAIR'],resume_safe:true,validation_retry:false},
 {batch_id:'MOCK_BATCH',document_id:'DOC_SYNTHETIC_2',version_id:'V03',title:'文件版本与引用核对指南',filename:'文件版本与引用核对指南.pdf',relative_path:'质量/文件版本与引用核对指南.pdf',queue:'NORMAL',status:'AVAILABLE',reasons:[],resume_safe:false,validation_retry:false},
]
export async function getManagedPipeline(){return {items:pipelineItems,total:pipelineItems.length,normal_remaining:1,exceptions:1,awaiting_adoption:1,available:1,batch_count:1,net_available_per_hour:8,human_interventions:1,scan_truncated:false,controller_continues_without_browser:true}}
const blocked=async()=>{throw Error('合成预览：此操作未连接真实服务')}
export const approveManagedRows=blocked,copyManagedTemplate=blocked,createManagedSpace=blocked,inspectManagedSource=blocked,precheckManagedUpload=blocked,resumeManagedBatch=blocked,uploadManagedGroup=blocked,verifyManagedReader=blocked
