from pymysql import connect
from pymysql.cursors import DictCursor
from config import config_const


class OpenDB(object):
    def __init__(self):
        super(OpenDB, self).__init__()
        # 初始化
        self.conn = connect(
            host=config_const['db_config']['host'],
            port=config_const['db_config']['port'],
            user=config_const['db_config']['user'],
            passwd=config_const['db_config']['passwd'],
            db=config_const['db_config']['db'],
            charset=config_const['db_config']['charset']
        )
        # 获取游标
        self.cs = self.conn.cursor(DictCursor)

    def __enter__(self):
        # 返回游标进行执行操作
        return self.cs

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 结束提交数据并关闭数据库
        self.conn.commit()
        self.cs.close()
        self.conn.close()


class ChainDb(object):
    def __init__(self, database):
        super(ChainDb, self).__init__()
        self.where_keys = ''
        self.where_vals = []
        self.params = '*'
        self.limit = ''
        self.order_by = ''
        self.group_by = ''
        if config_const['db_config']['pre']:
            self.database = config_const['db_config']['pre'] + database
        else:
            self.database = database

    # 查询条件拼接
    @staticmethod
    def _select(where, where_keys, where_vals, method='and'):
        is_method = 0
        where_method, where_compare = [], []
        for item in where.values():
            if isinstance(item, list) and len(item) > 1:
                # 判断条件类型，默认是and
                if len(item) > 2:
                    if len(item) == 3 and item[2] and (item[2] == 'and' or item[2] == 'or'):
                        where_method.append(item[2])
                    else:
                        where_method.append('and')
                else:
                    where_method.append('and')
                # 判断条件方式，大于或等于等等
                sign_res = False
                if item[0]:
                    compare_sign = ['>', '<', '=', '<>', '>=', '<=']
                    for sign in compare_sign:
                        if item[0] == sign:
                            sign_res = True
                            break
                if sign_res:
                    where_compare.append(item[0])
                else:
                    where_compare.append('=')
                # 条件值
                where_vals.append(item[1])
                is_method = 1
            else:
                where_vals.append(item)
                is_method = 0
        if is_method == 1:
            # 拼接and或or条件，最后一个去掉
            keys = list(where.keys())
            method_len = len(where_vals)
            for i in range(method_len):
                where_keys += keys[i] + where_compare[i] + '%s ' + (
                    where_method[i] if i <= method_len - 2 else '') + ' '
        else:
            # 拼接条件
            where_keys = (' ' + method + ' ').join([item + '=%s' for item in where.keys()])
        where_vals = tuple(where_vals)
        return {'keys': where_keys, 'vals': where_vals}

    # 执行mysql
    @staticmethod
    def query(sql=None, tuple_values=None):
        if not sql:
            raise Exception('sql语句不能为空')
        if tuple_values and not isinstance(tuple_values, tuple):
            raise Exception('参数类型必须是元组')
        try:
            with OpenDB() as cs:
                if tuple_values:
                    cs.execute(sql, tuple_values)
                else:
                    cs.execute(sql)
                return cs
        except Exception as e:
            return e

    # 查询条件
    def where(self, where=None, value=None, method='and'):
        where_keys, where_vals = '', []
        if value is not None:
            where = {where: value}
        # 判断参数
        if where and not isinstance(where, dict):
            raise Exception('查询条件必须是字典类型')
        if where:
            # 查询字段
            _select = self._select(where, where_keys, where_vals, method)
            where_keys, where_vals = _select['keys'], _select['vals']
        if hasattr(self, 'where_keys') and self.where_keys:
            self.where_keys += ' ' + method + ' ' + where_keys
            self.where_vals += where_vals
        else:
            self.where_keys = where_keys
            self.where_vals = where_vals
        return self

    # 查询字段
    def field(self, params=None):
        if not params:
            self.params = '*'
        else:
            if isinstance(params, list):
                params = ','.join(params)
            self.params = params
        return self

    # 分页
    def page(self, page=1, rows=10):
        self.limit = str((page - 1) * rows) + ',' + str(rows)
        return self

    # 归组
    def group(self, param=None):
        if not param:
            return self
        if not isinstance(param, str):
            raise Exception('参数必须是字符串类型')
        self.group_by = param
        return self

    # 排序
    def order(self, order_by=None):
        if not order_by:
            return self
        self.order_by = order_by
        return self

    # 格式化sql
    def format_sql(self):
        if not hasattr(self, 'params'):
            self.params = '*'
        # select * from user u left join class c on u.user_id = c.user_id where u.user_id = 1
        sql = "SELECT {} FROM {}".format(self.params, self.database)
        if hasattr(self, 'where_keys') and self.where_keys:
            sql += " WHERE {}".format(self.where_keys)
        if hasattr(self, 'order_by') and self.order_by:
            sql += " ORDER BY {}".format(self.order_by)
        if hasattr(self, 'group_by') and self.group_by:
            sql += " GROUP BY {}".format(self.group_by)
        if hasattr(self, 'limit') and self.limit:
            sql += " limit {}".format(self.limit)
        return sql

    # 查询多个数据
    def select(self):
        try:
            with OpenDB() as cs:
                sql = self.format_sql()
                if hasattr(self, 'where_vals') and self.where_vals:
                    print(sql % self.where_vals)
                    cs.execute(sql, self.where_vals)
                else:
                    cs.execute(sql)
                return cs.fetchall()
        except Exception as e:
            return e

    # 查询单个数据
    def find(self):
        try:
            with OpenDB() as cs:
                sql = self.format_sql()
                if self.where_vals:
                    cs.execute(sql, self.where_vals)
                else:
                    cs.execute(sql)
                return cs.fetchone()
        except Exception as e:
            return e

    # 查找单个字段
    def value(self, field=None):
        if not field:
            raise Exception('查询字段不能为空')
        try:
            with OpenDB() as cs:
                sql = self.format_sql()
                if self.where_vals:
                    cs.execute(sql, self.where_vals)
                else:
                    cs.execute(sql)
                row = cs.fetchone()
                if field not in row:
                    raise Exception('没有查询到该字段')
                return row[field]
        except Exception as e:
            return e

    # 新增数据
    def insert(self, data):
        if not data:
            raise Exception('新增内容不能为空')
        if not isinstance(data, dict) and not isinstance(data, list):
            raise Exception('参数必须是字典类型')
        if isinstance(data, list):
            # 批量插入数据处理
            if not data:
                raise Exception('列表内容不能为空')
            # 参数赋值
            long_item, long_data, values_list = 0, [], []
            # 循环获取字段最多的字典
            for item in data:
                item_len = len(item)
                if item_len > long_item:
                    long_item = item_len
                    long_data = item
            # 字段最多的字典不存在
            if not long_data:
                raise Exception('新增字段不能为空')
            # 获取字典keys值
            keys_list = list(long_data.keys())
            # 获取新增keys值和values占位符
            keys = ','.join(long_data.keys())
            values = ','.join(['%s' for i in range(len(long_data))])
            # 循环获取字段
            for item in data:
                item_new = []
                # 循环字段最多到列表
                for key in keys_list:
                    # 判断字段是否存在
                    has_key = item.get(key, -1)
                    if has_key == -1:
                        # 字段不存在
                        item_new.append('')
                    else:
                        # 字段存在
                        item_new.append(item[key])
                # 转换为元组后新增到新的元组
                values_list.append(tuple(item_new))
            values_list = tuple(values_list)
            is_more = 1
        else:
            # 单个插入数据处理
            keys = ','.join(data.keys())
            values_list = tuple(data.values())
            # 根据字段个数来生成相应的字符串占位符
            values = ','.join(['%s' for i in range(len(data))])
            is_more = 0
        # 添加数据
        try:
            with OpenDB() as cs:
                sql = "INSERT INTO {} ({}) VALUES ({})".format(self.database, keys, values)
                if is_more == 1:
                    # 批量插入
                    cs.executemany(sql, values_list)
                else:
                    # 单个插入
                    cs.execute(sql, values_list)
                if cs.rowcount <= 0:
                    raise Exception('新增内容为空，插入数据库失败')
                last_id = cs.lastrowid if cs.rowcount == 1 else cs.rowcount
                return last_id
        except Exception as e:
            return e

    # 更新内容
    def update(self, data=None):
        # 条件判断
        if not data:
            raise Exception('更新内容不能为空')
        if not isinstance(data, dict):
            raise Exception('参数必须是字典类型')
        if not hasattr(self, 'where_vals'):
            raise Exception('查询条件不能为空')
        # 更新字段
        set_keys = ','.join([item + '=%s' for item in data.keys()])
        set_vals = [item for item in data.values()]
        # 合并dict并转化为元组
        val_list = tuple(set_vals + list(self.where_vals))
        try:
            with OpenDB() as cs:
                sql = "UPDATE {} SET {} WHERE {}".format(self.database, set_keys, self.where_keys)
                row = cs.execute(sql, val_list)
                return row
        except Exception as e:
            return e

    # 删除数据
    def delete(self):
        try:
            with OpenDB() as cs:
                sql = "DELETE FROM {}".format(self.database)
                if hasattr(self, 'where_keys'):
                    sql += " WHERE {}".format(self.where_keys)
                    row = cs.execute(sql, self.where_vals)
                else:
                    row = cs.execute(sql)
                return row
        except Exception as e:
            return e
