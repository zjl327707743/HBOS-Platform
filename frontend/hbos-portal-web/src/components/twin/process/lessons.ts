import type { ProcessTopic } from "@/types/twin";

export interface LessonStep {
  id: string;
  label: string;
  start: number;
  duration: number;
  purpose: string;
  objects: string;
  observation: string;
  evidence: string;
  camera:
    | "overview"
    | "vessel"
    | "feed"
    | "vacuum"
    | "cip"
    | "sip"
    | "discharge"
    | "supply"
    | "return"
    | "attachment";
}
const step = (
  id: string,
  label: string,
  start: number,
  duration: number,
  purpose: string,
  objects: string,
  observation: string,
  evidence: string,
  camera: LessonStep["camera"],
): LessonStep => ({
  id,
  label,
  start,
  duration,
  purpose,
  objects,
  observation,
  evidence,
  camera,
});
const schematic =
  "旧项目原理示意与设备独立显示绑定；尺寸、动作与节奏为演示假设。";
const textOnly =
  "既有图纸文字候选 + 原理示意；本机回路、阀序、联锁与合格条件待核。";
export const topics: Record<
  ProcessTopic,
  { label: string; duration: number; steps: LessonStep[] }
> = {
  production: {
    label: "生产主线",
    duration: 60,
    steps: [
      step(
        "feed",
        "进料",
        0,
        12,
        "理解物料进入边界。",
        "进料路径、主罐候选与示意物料",
        "示意物料增加；路径不代表已核现场连接。",
        "既有流程名称候选 + 系统级 HDS；顺序不是批准配方。",
        "feed",
      ),
      step(
        "filter",
        "过滤",
        12,
        12,
        "理解液相通过介质、固相截留。",
        "简化过滤面、液相与固相示意",
        "液相逐步减少，固相留在过滤面上方；视觉量无实测单位。",
        schematic,
        "vessel",
      ),
      step(
        "wash",
        "洗涤",
        24,
        12,
        "理解洗涤、混合与排液。",
        "进料主管、示意搅拌与底部排液",
        "六段阅读节奏：进入、下降、混合、上升、排液、保留固体。",
        "系统级 HDS + 旧项目六段演示；次数、行程和结束条件待核。",
        "vessel",
      ),
      step(
        "dry",
        "干燥",
        36,
        12,
        "理解供热与气体移出的原理。",
        "主罐、真空路径及设备专属供热边界",
        "观察示意搅拌和气体移出；颜色不表示温度，没有干燥合格判定。",
        "系统级 HDS + 旧项目独立绑定；现场温压与联锁未提供。",
        "vacuum",
      ),
      step(
        "discharge",
        "出料",
        48,
        12,
        "理解出料观察边界。",
        "示意堵头、搅拌及出料开放边界",
        "堵头回缩、搅拌辅助出料；内部形状与真实行程待核。",
        "既有流程文字候选 + Owner 确认的原理表达；下游未核。",
        "discharge",
      ),
    ],
  },
  filtration: {
    label: "过滤原理",
    duration: 40,
    steps: [
      step(
        "suspension",
        "悬混液",
        0,
        10,
        "认识液相与固相。",
        "主罐候选、简化液相和固体",
        "两种颜色区分示意物相；颗粒数与比例均为演示假设。",
        schematic,
        "vessel",
      ),
      step(
        "separation",
        "固液分离",
        10,
        20,
        "理解过滤介质的截留作用。",
        "简化过滤面、湿料及底部排液边界",
        "液相穿过简化过滤面，固体保留；不代表本机内部结构。",
        schematic,
        "vessel",
      ),
      step(
        "wet-cake",
        "保留湿料",
        30,
        10,
        "观察过滤后的示意状态。",
        "湿料层与剩余液相",
        "保留湿料；不显示实测残液、质量衡算或结束阈值。",
        schematic,
        "vessel",
      ),
    ],
  },
  cip: {
    label: "CIP 清洗原理",
    duration: 24,
    steps: [
      step(
        "cip-supply",
        "供给管网",
        0,
        8,
        "理解清洗液供给用途。",
        "设备自身供给主干与顶部三路示意",
        "清洗液标记进入；供给补段与端点仍是示意。",
        textOnly,
        "cip",
      ),
      step(
        "cip-contact",
        "罐内冲洗",
        8,
        8,
        "理解壁面润湿与回液。",
        "顶部三路、罐壁作用区与底部回液",
        "空设备原理示意；不认定喷头型号或真实清洗覆盖。",
        textOnly,
        "vessel",
      ),
      step(
        "cip-return",
        "回液边界",
        16,
        8,
        "识别未核的下游边界。",
        "底部回液开放边界",
        "回液离开示意区域；下游去向、阀序与洁净判定待核。",
        textOnly,
        "cip",
      ),
    ],
  },
  sip: {
    label: "SIP 灭菌原理",
    duration: 24,
    steps: [
      step(
        "sip-inlet",
        "进气说明",
        0,
        8,
        "理解蒸汽供给的概念。",
        "设备自身 PS 候选供给与进气补段",
        "浅色标记向下进入；不显示真实压力或阀位。",
        textOnly,
        "sip",
      ),
      step(
        "sip-contact",
        "罐内接触",
        8,
        8,
        "理解自上而下的接触示意。",
        "罐内概念作用区",
        "原理标记逐步充满；不表达真实温场或保持条件。",
        textOnly,
        "vessel",
      ),
      step(
        "sip-outlet",
        "局部排出",
        16,
        8,
        "识别排出与凝结的开放边界。",
        "下部排水候选与局部排出",
        "下部排出示意；PSC、放空、排污不拼成已核闭环。",
        textOnly,
        "sip",
      ),
    ],
  },
  jacket: {
    label: "M607B 夹套热水供回",
    duration: 46,
    steps: [
      step(
        "overview",
        "总览",
        0,
        8,
        "认识夹套热水供回的讲解边界。",
        "M607B、供回名称候选",
        "浅绿只表示当前讲解对象；名称映射不等于现场连通。",
        "旧项目五步讲解；102 Tie-in 与 P&ID 图纸候选。",
        "overview",
      ),
      step(
        "explain_supply",
        "供水定位",
        8,
        10,
        "定位已有供水名称候选。",
        "TP-17 · HWS 供水名称候选",
        "观察已登记的 7 个普通管路候选，不含支架、保温或照片拟合层；三维无流向。",
        "102 Tie-in 平面/立面第 1 页；名称映射，端点与方向未核。",
        "supply",
      ),
      step(
        "explain_transfer",
        "夹套传热",
        18,
        10,
        "理解夹套侧与壁面交换热量。",
        "主罐外形候选与独立概念说明",
        "主罐着色只作观察；不画内部构造、温场，也不把热水画入产品腔体。",
        "旧项目传热概念；夹套口与内部位置待核。",
        "vessel",
      ),
      step(
        "explain_return",
        "回水定位",
        28,
        10,
        "定位已有回水名称候选。",
        "TP-19 · HWR 回水名称候选",
        "观察 7 个候选；它们不代表已验证的完整回程，三维无流向。",
        "102 Tie-in 平面/立面第 1 页；B2b、连续段与共用支路待核。",
        "return",
      ),
      step(
        "recap",
        "回顾",
        38,
        8,
        "复核用途与待核事项。",
        "供水、壁面传热概念、回水候选",
        "阀门映射、B2a/B2b、冷热共用边界待核；结束不表示设备停机。",
        "复用旧项目五步阅读节奏；供回温压、流量与阀位均缺失。",
        "overview",
      ),
    ],
  },
  attachment: {
    label: "顶部附件候选",
    duration: 24,
    steps: [
      step(
        "attachment-context",
        "位置与边界",
        0,
        8,
        "认识独立附件候选与设备的观察关系。",
        "M660B 已登记几何候选",
        "只观察外形与位置；独立身份不等于业务部件关联已经核验。",
        "既有 a2 成员和候选目录；几何适用性待核。",
        "overview",
      ),
      step(
        "attachment-focus",
        "局部观察",
        8,
        8,
        "观察已登记外部几何。",
        "现有附件候选组",
        "可聚焦或隔离观察外形；没有滤芯内部或真实气流动画。",
        "候选目录几何定位；内部、接口和功能映射未核。",
        "attachment",
      ),
      step(
        "attachment-recap",
        "恢复上下文",
        16,
        8,
        "回到设备观察范围。",
        "当前设备与独立附件候选",
        "恢复显示并回总览；未知节点仅给设备级知识上下文。",
        "已有身份与批准成员范围；不提升资料权限。",
        "overview",
      ),
    ],
  },
};

export function lessonAt(topic: ProcessTopic, time: number): LessonStep {
  const definition = topics[topic];
  return (
    [...definition.steps].reverse().find((s) => time >= s.start) ??
    definition.steps[0]!
  );
}
export function durationFor(topic: ProcessTopic = "production") {
  return topics[topic].duration;
}
export const lectureRoutes = {
  principles: {
    label: "过滤 → 生产 → 清洗 → 灭菌",
    topics: ["filtration", "production", "cip", "sip"] as ProcessTopic[],
  },
  cleaning: { label: "清洗 → 灭菌", topics: ["cip", "sip"] as ProcessTopic[] },
};
