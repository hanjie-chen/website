from datetime import date
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import String, Date, Text, Integer
from flask_sqlalchemy import SQLAlchemy


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


# 文章元数据
class Article_Meta_Data(db.Model):
    # 指定数据模型在数据库中的表名称 如果未指定那么为类名称的小写
    __tablename__ = "article_meta_data"
    # 主键 但是无需为其赋值 SQLite数据库会自动为其生成一个唯一的值
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 文章标题 最长不超过100个字 默认nullable=False
    title: Mapped[str] = mapped_column(String(100))

    # 文章作者 最长不超过50个字符
    author: Mapped[str] = mapped_column(String(50))

    # 文章指导者 存在Optional 默认nullable=True
    instructor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 文章封面链接 真实image存储地址 由于特别设计，所以可以由category+相对路径转换而来
    # 例如 PythonLearn/PythonPackage/Flask/images/cover-image.png 其 cover_image_url = "redered-articles/PythonLearn-PythonPackage-Flask/images/cover-image.png"
    cover_image_url: Mapped[str] = mapped_column(String(100))

    # 文章发布时间
    rollout_date: Mapped[date] = mapped_column(Date)

    # 表示文章最后更新的日期 只精确到年月日 --> 使用文件最后修改日期 不显式指定
    ultimate_modified_date: Mapped[date] = mapped_column(Date)

    # 文章内容简介
    brief_introduction: Mapped[str] = mapped_column(Text)

    # 文章分类 是文章的路径
    # 例如 PersonalActicles/PythonLearn/PythonPackage/Flask/Basic.md 其 category = "PythonLearn/PythonPackage/Flask"
    # 暂时定义最大长度 1024 个字符
    category: Mapped[str] = mapped_column(String(1024))

    # 文章文件相对路径（用于唯一标识）
    # 例如 PythonLearn/PythonPackage/Flask/Basic.md
    file_path: Mapped[str] = mapped_column(String(1024), unique=True)

    # 文章内容哈希，用于判断是否需要更新
    content_hash: Mapped[str] = mapped_column(String(64))

    # 文章分类 使用 mptt 待开发和测试
    # 关于category 在metadata中并不显示指定 而是根据路径来 比如说 ~/PersonalArticles/PythonLearn/PythonPackage/Basic.md
    # 那么这篇Basic.md 的category其实就是 PythonLearn --> PythonPackage
    # category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    # category = db.relationship('Category')

    def __repr__(self):
        return f"<Article {self.title}>"


# mptt 待开发和测试
# class Article_Category(db.Model):
#     __tablename__ = 'articl_category'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), nullable=False, unique=True)
#     parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
#     children = db.relationship('Category')
