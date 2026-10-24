# 不在包初始化时 import 子模块：module.conf 在构造 settings 之前要 import
# module.update.v4，而其它子模块依赖 module.conf，会形成循环。
