import pymysql  # 引入pymysql模块
from dbutils.pooled_db import PooledDB
from threading import Lock
from loguru import logger


# 数据库配置文件

class DatabasePool:
    def __init__(self, logger, DB_HOST, DB_PORT, DB_DATABASE, DB_USER, DB_PASSWORD):
        self.pool = PooledDB(
            creator=pymysql,
            maxconnections=8,
            mincached=2,
            maxcached=5,
            maxshared=3,
            blocking=True,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        self.lock = Lock()
        self.logger = logger

    def _get_connection(self):
        try:
            return self.pool.connection()
        except Exception as e:
            self.logger.error("Failed to get connection from pool: %s" % e)
            return None

    @staticmethod
    def to_dict(data):
        if isinstance(data, dict):
            return data
        elif hasattr(data, '__table__'):
            return {column.name: getattr(data, column.name) for column in data.__table__.columns if
                    getattr(data, column.name) is not None}
        else:
            raise TypeError("Unsupported data type for conversion to dictionary.")

    def _prepare_data_list(self, data_dict, data_list):
        if data_dict is not None:
            return [self.to_dict(data_dict)]
        elif data_list is not None:
            return [self.to_dict(item) for item in data_list]
        else:
            raise ValueError("Either data_dict or data_list must be provided.")

    def execute_many_or_loop(self, table, sql, values, return_ids=False, operation='insert'):
        """
        执行批量操作或循环操作以返回ID。
        :param table: 表名。
        :param sql: SQL语句模板。
        :param values: 值列表，每个元素都是一个记录的值。
        :param return_ids: 是否返回每条记录的ID。
        :param operation: 操作类型，'insert' or 'update'。
        :return: 如果return_ids为True，则返回ID列表；否则返回None。
        """
        ids = []
        query_result = False
        conn = self._get_connection()
        if conn is None:
            return ids

        try:
            with conn.cursor() as cursor, self.lock:
                if return_ids and operation == 'insert':
                    for value in values:
                        try:
                            cursor.execute(sql, value)
                            conn.commit()
                            provided_id = value.get("id") if "id" in value else cursor.lastrowid
                            ids.append(provided_id)
                            # self.logger.info(f"{operation} success【{table}】-> {ids} -> {value}")
                            self.logger.info(f"{operation} success【{table}】")
                        except cursor.IntegrityError as err:
                            self.logger.warning(f"{operation} fail【{table} -> {value} 数据存在！")
                        except Exception as e:
                            print(e)
                            # print("table", table)
                            # print("sql", sql)
                            # print("values", values)
                            conn.rollback()
                            self.logger.error(f"{operation} failed: {e} for {value}")

                elif operation == "query":
                    try:
                        if values:
                            result = cursor.execute(sql, values)
                        else:
                            result = cursor.execute(sql)
                        if result:
                            query_result = cursor.fetchall()
                            columns = [column[0] for column in cursor.description]
                            # 将结果转换为字典列表
                            rows_as_dict = []
                            for row in query_result:
                                row_dict = dict(zip(columns, row))
                                rows_as_dict.append(row_dict)
                            query_result = rows_as_dict
                            return query_result
                    except Exception as e:
                        # print("table", table)
                        # print("sql", sql)
                        # print("values", values)
                        self.logger.error(f"{operation} failed: {e} for {values}")

                else:
                    cursor.executemany(sql, values)
                    self.logger.info(f"{operation} success【{table}】-> {values[0]} ")
                    conn.commit()

        except cursor.IntegrityError as err:
            # print("table", table)
            # print("sql", sql)
            # print("values", values)
            # 这里捕获到的是与数据完整性相关的错误，比如唯一约束被违反
            # self.logger.warning(f"Skipping due to unique constraint violation:{err}")
            pass

        except Exception as e:
            # print("table", table)
            # print("sql", sql)
            # print("values", values)
            conn.rollback()
            self.logger.error(f"Database operation failed:{e}")

        finally:
            conn.close()
            if query_result:
                return query_result
            return ids if return_ids and ids else None

    def _get_ids_for_update(self, table, condition):
        condition_parts = ' AND '.join([f"{k} = %s" for k in condition.keys()])
        sql = f"SELECT id FROM {table} WHERE {condition_parts}"
        values = list(condition.values())
        ids = None
        conn = self._get_connection()
        if conn is None:
            return ids

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                ids = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error("Failed to get IDs for update: %s", e)

        finally:
            conn.close()
            return ids

    def insert(self, table, data_dict: dict = None, data_list=None, return_ids: bool = False):
        """
            插入mysql数据库。
            :param table: 表名。
            :param data_dict: 单个插入数据 str。
            :param data_list: 批量插入数据 list。
            :param return_ids: 是否返回每条记录的ID bool。
            :return: 如果return_ids为True，则返回ID列表；否则返回None。
        """
        ids = None
        try:
            data_dicts = self._prepare_data_list(data_dict, data_list)

            keys = data_dicts[0].keys()
            values = [[item[key] for key in keys] for item in data_dicts]
            placeholders = ', '.join(['%s'] * len(keys))
            columns = ', '.join(keys)
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            ids = self.execute_many_or_loop(table, sql, values, return_ids, 'insert')
            # return ids
        except Exception as E:
            self.logger.error("insert failed: %s" % E)
        finally:
            return ids

    def update(self, table, condition, data_dict=None, data_list=None, return_ids=False):
        """
            更新mysql数据库。
            :param table: 表名。
            :param condition: 更新字段 dict。
            :param data_dict: 单个更新数据 str。
            :param data_list: 批量更新数据 list。
            :param return_ids: 是否返回每条记录的ID bool。
            :return: 如果return_ids为True，则返回ID列表；否则返回None。
        """

        ids = None
        if return_ids:
            ids = self._get_ids_for_update(table, condition)
            if not ids:
                self.logger.warning(f"update 【{table}】失败，未找到需要更新的数据, 更新key -> {condition}")
                return

        try:
            data_dicts = self._prepare_data_list(data_dict, data_list)
            set_parts = ', '.join([f"{k} = %s" for k in data_dicts[0].keys()])
            condition_parts = ' AND '.join([f"{k} = %s" for k in condition.keys()])
            values = [(list(item.values()) + list(condition.values())) for item in data_dicts]

            sql = f"UPDATE {table} SET {set_parts} WHERE {condition_parts}"

            self.execute_many_or_loop(table, sql, values, operation='update')

        except Exception as E:
            self.logger.error("update failed: %s" % E)
            ids = None

        finally:
            return ids

    def update_status(self, table, condition, data_dict=None, data_list=None, return_ids=False, sql=''):
        """
            更新mysql数据库。
            :param table: 表名。
            :param condition: 更新字段 dict。
            :param data_dict: 单个更新数据 str。
            :param data_list: 批量更新数据 list。
            :param return_ids: 是否返回每条记录的ID bool。
            :return: 如果return_ids为True，则返回ID列表；否则返回None。
        """

        ids = None
        if return_ids:
            ids = self._get_ids_for_update(table, condition)
            if not ids:
                self.logger.warning(f"update 【{table}】失败，未找到需要更新的数据, 更新key -> {condition}")
                return

        try:
            data_dicts = self._prepare_data_list(data_dict, data_list)

            set_parts = ', '.join([f"{k} = %s" for k in data_dicts[0].keys()])
            condition_parts = ' AND '.join([f"{k} = %s" for k in condition.keys()])
            values = [(list(item.values()) + list(condition.values())) for item in data_dicts]
            if condition_parts:
                sql = f"UPDATE {table} SET {set_parts} WHERE {condition_parts}" + sql
            else:
                sql = f"UPDATE {table} SET {set_parts} WHERE {sql}"

            self.execute_many_or_loop(table, sql, values, operation='update')

        except Exception as E:
            self.logger.error("update failed: %s" % E)
            ids = None

        finally:
            return ids

    def query(self, table, condition, query_criteria=None, get_results=False, sql=None):
        """
            更新mysql数据库。
            :param table: 表名。
            :param condition: 查询字段 dict。
            :param query_criteria: 指定查询特定的值 list ,strx`x`
            :return: 如果return_ids为True，则返回ID列表；否则返回None。
        """
        query_result = False
        try:
            if not sql:
                if condition:
                    condition_str = ' AND '.join([f"{key} = %s" for key in condition.keys()])
                if query_criteria:
                    if isinstance(query_criteria, list):
                        query_criteria = query_criteria
                        key_str = ' ,'.join([key for key in query_criteria])
                    elif isinstance(query_criteria, str):
                        key_str = query_criteria
                    else:
                        key_str = ' ,'.join([key for key in condition.keys()])
                else:
                    key_str = "*"
                if condition:
                    sql = f"SELECT {key_str} FROM {table} WHERE {condition_str}"
                    values = list(condition.values())

                else:
                    sql = f"SELECT {key_str} FROM {table}"
                    values = list()
            else:
                values = list()
            query_result = self.execute_many_or_loop(table, sql, values, operation='query')
            if not get_results and query_result:
                query_result = True
        except Exception as E:
            self.logger.error("update failed: %s" % E)

        finally:
            return query_result

    def upsert(self, table, condition, data_dict=None, data_list=None):
        """
        插入或更新数据库。
        :param table: 表名。
        :param condition: 更新字段 dict。
        :param data_dict: 单个插入/更新数据 dict。
        :param data_list: 批量插入/更新数据 list。
        """
        # 获取表的所有字段名
        try:
            data_dicts = self._prepare_data_list(data_dict, data_list)
            keys = data_dicts[0].keys()
            values = [[item[key] for key in keys] for item in data_dicts]

            # 构造插入和更新的字段名及其值
            placeholders = ', '.join(['%s'] * len(keys))
            columns = ', '.join(keys)
            updates = ', '.join([f"{key} = VALUES({key})" for key in keys])

            # 构造SQL语句
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"

            # 执行插入或更新操作
            self.execute_many_or_loop(table, sql, values, operation='upsert')

        except Exception as E:
            self.logger.error(f"Upsert failed: {E}")

    def query_table_data_count(self, table):
        sql = f"SELECT COUNT(*) FROM {table}"
        query_result = self.execute_many_or_loop(table, sql, list(), operation='query')
        if query_result:
            data = list(query_result[0].values())[0]
        else:
            data = 0
        return data

    def query_table_data_value_count(self, table, search_value):
        sql = f"SELECT COUNT(*) FROM {table} WHERE id LIKE '%{search_value}%';"
        query_result = self.execute_many_or_loop(table, sql, list(), operation='query')
        # print(query_result)
        if query_result:
            data = list(query_result[0].values())[0]
        else:
            data = 0
        return data
