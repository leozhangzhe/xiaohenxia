# -*- coding: utf-8 -*-
"""
泄露检测模块 - 基于 leak-check 开源项目 (https://github.com/garinasset/leak-check)
用于检测个人信息是否在已知数据泄露事件中被暴露。
"""

import os
import re
import sqlite3
from typing import Optional, List, Dict, Set, Sequence


# ============================================================
# 脱敏函数（移植自 leak-check/lib/masking.py）
# ============================================================

def mask_phone(v: str) -> str:
    if not v or len(v) < 7:
        return "***"
    return v[:2] + "*******" + v[-2:]


def mask_email(v: str) -> str:
    if not v or "@" not in v:
        return "***"
    name, domain = v.split("@", 1)
    if len(name) <= 2:
        name_mask = name[0] + "***"
    else:
        name_mask = name[:2] + "***"
    return f"{name_mask}@{domain}"


def mask_id(v: str) -> str:
    if not v or len(v) < 10:
        return "***"
    return v[:2] + "********" + v[-2:]


def mask_number(v: str) -> str:
    v = str(v)
    if len(v) <= 3:
        return "*" * len(v)
    return "*" * (len(v) - 3) + v[-3:]


def mask_name(v: str) -> str:
    if not v:
        return "***"
    if len(v) == 1:
        return "*"
    return "*" + v[-1]


def mask_car(v: str) -> str:
    if not v:
        return "***"
    v = str(v).strip()
    if len(v) <= 2:
        return v[0] + "*"
    return v[:2] + "*" * (len(v) - 2)


def mask_address(v: str) -> str:
    if not v:
        return "***"
    return v[:2] + "****" if len(v) > 2 else v + "****"


def mask_value(field: str, v: Optional[str]) -> str:
    if not v:
        return ""
    v = str(v).strip()
    if not v:
        return ""
    if field == "phone":
        return mask_phone(v)
    if field == "email":
        return mask_email(v)
    if field == "id":
        return mask_id(v)
    if field in ("qq", "weibo"):
        return mask_number(v)
    if field in ("name", "nickname", "receiver", "contact"):
        return mask_name(v)
    if field == "car":
        return mask_car(v)
    if field in ("address", "company"):
        return mask_address(v)
    return v


def mask_list(field: str, values) -> List[str]:
    return list({
        mask_value(field, v)
        for v in values
        if v is not None and str(v).strip()
    })


# ============================================================
# 输入类型自动识别（移植自 leak-check/models/request.py）
# ============================================================

def detect_query_type(q: str) -> Optional[str]:
    """自动识别输入类型：phone / email / id / qq"""
    if not q or not q.strip():
        return None
    q = q.strip()
    cleaned = re.sub(r"[ \-\(\)]", "", q)

    cn_phone_pattern = r"^1\d{10}$"
    intl_phone_pattern = r"^\+\d{6,15}$"
    phone_pattern = rf"(?:{cn_phone_pattern})|(?:{intl_phone_pattern})"

    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    mainland_id_pattern = r"^\d{17}[\dXx]$"
    taiwan_id_pattern = r"^[A-Z][12]\d{8}$"
    id_pattern = rf"(?:{mainland_id_pattern})|(?:{taiwan_id_pattern})"

    qq_pattern = rf"^(?!{phone_pattern}$)\d{{5,11}}$"

    if re.fullmatch(phone_pattern, cleaned):
        return "phone"
    elif re.fullmatch(email_pattern, q):
        return "email"
    elif re.fullmatch(id_pattern, cleaned):
        return "id"
    elif re.fullmatch(qq_pattern, cleaned):
        return "qq"
    else:
        return None


# ============================================================
# SQLite 数据库查询（移植自 leak-check/db/crud.py）
# ============================================================

class LeakCheckDB:
    """泄露检测数据库访问层"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "leak-check.db"
            )
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """确保数据库目录和表存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source (
                    id INTEGER PRIMARY KEY,
                    source TEXT DEFAULT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS person (
                    rowid INTEGER PRIMARY KEY,
                    id TEXT DEFAULT NULL,
                    name TEXT DEFAULT NULL,
                    receiver TEXT DEFAULT NULL,
                    nickname TEXT DEFAULT NULL,
                    phone TEXT DEFAULT NULL,
                    address TEXT DEFAULT NULL,
                    car TEXT DEFAULT NULL,
                    email TEXT DEFAULT NULL,
                    qq INTEGER DEFAULT NULL,
                    weibo INTEGER DEFAULT NULL,
                    contact TEXT DEFAULT NULL,
                    company TEXT DEFAULT NULL,
                    source_id INTEGER DEFAULT 0,
                    FOREIGN KEY (source_id) REFERENCES source(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_person_phone ON person(phone)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_person_email ON person(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_person_qq ON person(qq)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_person_id ON person(id)")
            conn.commit()
        finally:
            conn.close()

    def get_record_count(self) -> int:
        """获取数据库总记录数"""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT MAX(rowid) FROM person").fetchone()
            return row[0] if row and row[0] else 0
        finally:
            conn.close()

    def search_persons(
        self,
        q: str,
        query_type: str = None,
        max_depth: int = 2,
        max_records: int = 64,
        threshold: int = 12
    ) -> List[Dict]:
        """
        BFS 深度查询泄露记录，返回脱敏后的聚合结果。

        Args:
            q: 查询值
            query_type: 查询类型 (phone/email/id/qq)，None 则自动识别
            max_depth: 最大 BFS 扩散层数
            max_records: 最大返回记录数
            threshold: 数据源阈值

        Returns:
            脱敏后的聚合结果字典
        """
        if query_type is None:
            query_type = detect_query_type(q)
        if query_type is None:
            return {"error": "无法识别输入类型，请输入手机号、邮箱、身份证号或QQ号"}

        # 清洗输入
        cleaned = re.sub(r"[ \-\(\)]", "", q.strip())
        if query_type != "email":
            q = cleaned

        conn = sqlite3.connect(self.db_path)
        try:
            # 初始化字段集合
            id_set: Set[str] = {q.upper(), q.lower()} if query_type == "id" else set()
            phone_set: Set[str] = {q} if query_type == "phone" else set()
            email_set: Set[str] = {q} if query_type == "email" else set()
            qq_set: Set[str] = set()
            if query_type == "qq":
                try:
                    qq_set = {int(q)}
                except ValueError:
                    return {"error": "QQ号格式错误"}

            all_persons: Dict[int, dict] = {}
            current_depth = 0

            while current_depth < max_depth:
                current_depth += 1
                new_ids, new_phones, new_emails, new_qqs = set(), set(), set(), set()

                results = []

                if id_set:
                    placeholders = ",".join(["?"] * len(id_set))
                    results += conn.execute(
                        f"SELECT rowid, id, name, receiver, nickname, phone, address, car, email, qq, weibo, contact, company, source_id FROM person WHERE id IN ({placeholders})",
                        list(id_set)
                    ).fetchall()

                if phone_set:
                    placeholders = ",".join(["?"] * len(phone_set))
                    results += conn.execute(
                        f"SELECT rowid, id, name, receiver, nickname, phone, address, car, email, qq, weibo, contact, company, source_id FROM person WHERE phone IN ({placeholders})",
                        list(phone_set)
                    ).fetchall()

                if email_set:
                    placeholders = ",".join(["?"] * len(email_set))
                    results += conn.execute(
                        f"SELECT rowid, id, name, receiver, nickname, phone, address, car, email, qq, weibo, contact, company, source_id FROM person WHERE email IN ({placeholders})",
                        list(email_set)
                    ).fetchall()

                if qq_set:
                    placeholders = ",".join(["?"] * len(qq_set))
                    results += conn.execute(
                        f"SELECT rowid, id, name, receiver, nickname, phone, address, car, email, qq, weibo, contact, company, source_id FROM person WHERE qq IN ({placeholders})",
                        list(qq_set)
                    ).fetchall()

                has_new_data = False

                for row in results:
                    rid = row[0]
                    if rid in all_persons:
                        continue

                    # 获取泄露来源
                    source_name = ""
                    if row[13]:
                        src_row = conn.execute(
                            "SELECT source FROM source WHERE id = ?", (row[13],)
                        ).fetchone()
                        if src_row and src_row[0]:
                            source_name = src_row[0]

                    all_persons[rid] = {
                        "id": row[1], "name": row[2], "receiver": row[3],
                        "nickname": row[4], "phone": row[5], "address": row[6],
                        "car": row[7], "email": row[8], "qq": row[9],
                        "weibo": row[10], "contact": row[11], "company": row[12],
                        "source": source_name
                    }
                    has_new_data = True

                    # 收集下一层
                    if row[1] and row[1] not in id_set:
                        new_ids.add(row[1])
                    if row[5] and row[5] not in phone_set:
                        new_phones.add(row[5])
                    if row[8] and row[8] not in email_set:
                        new_emails.add(row[8])
                    if row[9] and row[9] not in qq_set:
                        new_qqs.add(row[9])

                if len(all_persons) >= max_records:
                    break
                if not has_new_data:
                    break

                id_set = new_ids
                phone_set = new_phones
                email_set = new_emails
                qq_set = new_qqs

            # 脱敏聚合
            persons = list(all_persons.values())
            if not persons:
                return {
                    "found": False,
                    "query_type": query_type,
                    "message": "未在已知泄露数据库中发现相关记录"
                }

            # 收集所有泄露来源
            sources = list({
                p["source"]
                for p in persons
                if p["source"]
            })

            return {
                "found": True,
                "query_type": query_type,
                "total_records": len(persons),
                "source_count": len(sources),
                "sources": sources,
                "data": {
                    "id": mask_list("id", (p["id"] for p in persons)),
                    "name": mask_list("name", (p["name"] for p in persons)),
                    "receiver": mask_list("receiver", (p["receiver"] for p in persons)),
                    "nickname": mask_list("nickname", (p["nickname"] for p in persons)),
                    "phone": mask_list("phone", (p["phone"] for p in persons)),
                    "email": mask_list("email", (p["email"] for p in persons)),
                    "qq": mask_list("qq", (p["qq"] for p in persons)),
                    "weibo": mask_list("weibo", (p["weibo"] for p in persons)),
                    "address": mask_list("address", (p["address"] for p in persons)),
                    "car": mask_list("car", (p["car"] for p in persons)),
                    "contact": mask_list("contact", (p["contact"] for p in persons)),
                    "company": mask_list("company", (p["company"] for p in persons)),
                }
            }

        finally:
            conn.close()
