# Dev
为了让工具保持与时俱进，支持3.6开始的所有版本，我们需要时刻关注Blender的API变化：

- 4.3 to 4.4
- https://docs.blender.org/api/4.4/change_log.html#change-log
- 4.2 to 4.3
- https://docs.blender.org/api/4.3/change_log.html#change-log
- 4.1 to 4.2
- https://docs.blender.org/api/4.2/change_log.html#to-4-2
- 4.0 to 4.1
- https://docs.blender.org/api/4.1/change_log.html
- 3.6 to 4.0 
- https://docs.blender.org/api/4.0/change_log.html#change-log

# Blender下载地址

- https://www.blender.org/support/
- https://docs.blender.org/api/3.6/
- https://docs.blender.org/api/4.2/

# 开发必备插件
- https://github.com/JacquesLucke/blender_vscode              (推荐)
- https://github.com/BlackStartx/PyCharm-Blender-Plugin       (也能用，但不推荐)


# Blender插件开发中的缓存问题

在使用VSCode进行Blender插件开发中，会创建一个指向项目的软连接，路径大概如下：

C:\Users\Administrator\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons

在插件架构发生大幅度变更时可能导致无法启动Blender，此时需要手动删掉插件缓存的这个软链接。

# 文件夹命名大小写问题 

所有的文件夹都必须小写，因为git无法追踪文件夹名称大小写改变的记录

# 插件架构设计

本插件的目的是能够同时支持多个游戏，并且要在功能和使用流程上，完全不逊色于其他工具，例如XXMI-Tools或者WWMI-Tools，
要实现这一点，就必须实现以下架构，当然代码仍在不断开发改进中。

- 由于是小范围分享的插件，并未有公开打算，所以不添加自动更新功能。
- 各个游戏的导入流程和Mod生成流程必须拆分开来，所有基础功能最小的单元拆分为工具类，高级一点的拆分为帮助类。
帮助类的功能是比较复杂的实现一个功能，工具类则只负责特定小功能实现，比如字符串分割是一个工具类功能，导入顶点组权重到mesh是一个帮助类功能。
也就是说，帮助类是在工具类基础上进行了逻辑封装，也可以理解为Service层
最后是应用层，也就是用户操作的UI层级。


# Properties的设计和使用问题

我们不得不给把Properties分开放到不同类中，并提供classmethod来直接进行调用。

如果不这样设计的话，在其中一个Property遭到废弃或者发生大幅度变更时，

如果修改代码的时候不注意，就会导致部分地方没有完全修改，

设计成现在这样就能避免这些问题，用法和声明上都有了统一的规范。

# Jinja2的ini模板问题

我们不模仿XXMI-Tools和WWMI-Tools使用Jinja2的ini模板，
以便于在生成Mod逻辑发生变更后，能够第一时间通过修改代码来同步特性。

我们的项目尽可能遵循奥卡姆剃刀原理，不引入额外的组件和学习成本，
尽可能让每个人拿到源码后都能像滑雪一样顺畅的读完整个逻辑并理解大概原理，
除非到了哪天由于重要的特性不得不引入，否则暂时不加入Jinja2模板ini功能。




