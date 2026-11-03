# HTML交互功能契约

## 模块编辑

使用侧栏EDIT切换布局编辑，移除旧左下角仅改文字的工具。编辑时显示模块轮廓；单击选中、顶部手柄拖动、八方向边角调整宽高；提供X/Y/宽/高数值输入、双击改字、撤销/重做、置顶、还原模块、保存HTML。箭头微移，Shift＋箭头加大步长；快捷键不能打断输入。

以固定画布坐标计算鼠标位移，除以父容器显示比例，约束边界与最小尺寸。保留字号，改变模块高度不自动缩小全部内容；溢出需提醒。需要覆盖模板!important几何时使用受控行内!important。明确模块粒度：一个组合图/表可以作为一整个模块；不自动宣称所有内部单元都能像PPT一样拖拽。

进入PRESENT或切换语言自动退出编辑。提供临时本机草稿，使用文档独立键；保存HTML写入文字和几何，移除编辑轮廓、选择框及临时状态，保留封面/资源/功能。新导出文档使用新修订标识，避免旧草稿覆盖新文件。重新打开后保持编辑结果，并可继续编辑。

## 持续倒计时

分钟输入默认60，旁边只显示m。首次PRESENT开始，以绝对截止时间计算；退出、重进、切页、窗口失焦均不暂停或重置。只有重新输入合法分钟数重置，重新输入相同值也算；下次PRESENT启动新时长。拒绝空、非有限、零或负数，离开无效输入时恢复上次合法值。

封面不显示倒计时，但时间继续走。内容页右上角显示：腾讯体W7、22px、黑色；默认透明底；白底内容页可保留白底，无阴影。通过当前页的 `data-timer-background="white"` 显式启用白底，切页后同步更新；封面始终隐藏。控件不参与页面缩放与导出。不要改回24px、蓝色或显眼的阴影卡片。

总页数包含封面，currentPage从1开始。`pageShare=(totalPages-currentPage)/totalPages`；`timeShare=max(0,deadline-now)/initialDuration`。当`pageShare-timeShare>0.15`变红并轻微闪烁。这是15个百分点，不是乘以85%。例如100分钟100页，第60页剩40%页，低于25分钟才警示，正好25分钟不触发。

采用约1.8秒缓慢透明度变化，尊重reduced-motion；进度追回时清除预警；时间到显示0:00红色，不出现负数。封面隐藏优先于预警。打印/PPT不带计时器。保存HTML保留设定分钟数，不携带正在运行的截止时间。

## 参考代码接入

`assets/html/module-layout-editor.js`、`content-modules.js`、`countdown.js`、`page-numbers.js`及同目录CSS来自已验证的汇报实现，包含特定DOM约定；不是自动安装器。

接入顺序：内嵌 `assets/html/palette.css` 并统一覆盖已确认主题 → 定义字体和壳层 → 构建页面内容 → 创建Shadow DOM内容模块 → 语言/投屏控制器 → 编辑器 → 页码与计时器节点 → 计时逻辑。通用页面节点为`.brief-section`，封面id为cover；壳层含aside/main、layout-edit-toggle、sidebar-present、present-tools、presentation-minutes；body.presentation表示投屏。语言在html的data-language中，中文内容适配器为`.tc-content-host[data-page-id]`，每个host包含template，Shadow DOM中有#canvas/.slide/.title/.claim/.body/.box；共享样式template id为tc-page-style。

对不同报告先适配这些选择器、语言回调和页序；把项目名、年份、文件名、草稿键作为文档配置，不复制业务内容。当前参考编辑器支持中文内容模块，封面和英文视图不自动可编辑；需要时分别实现适配器。不要把当前范围描述成全页面元素编辑。

先测试数值坐标、宽高、双击文字、撤销、保存重开，再实际拖动与缩放。此前参考实现的数值编辑和保存已实测；真实指针拖动尚未获得成功自动化验证，复用后必须继续验证，不能凭代码存在就称已通过。
