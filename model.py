import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + os.path.join(app.instance_path, 'flaskr.sqlite')
db = SQLAlchemy(app)
print(db)


class Story(db.Model):
    __tablename__ = 'story'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('story_category.id'), nullable=False)
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(255))
    length = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class StoryQuestion(db.Model):
    __tablename__ = 'story_question'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'))
    content = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class StoryCategory(db.Model):
    __tablename__ = 'story_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Voice(db.Model):
    __tablename__ = 'voice'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    voice_desc = db.Column(db.String(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class StoryAudio(db.Model):
    __tablename__ = 'story_audio'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    voice_id = db.Column(db.Integer, db.ForeignKey('voice.id'), nullable=False)
    audio_path = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    sex = db.Column(db.Integer)
    phone = db.Column(db.Integer)
    email = db.Column(db.String(255))
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Dialogue(db.Model):
    __tablename__ = 'dialogue'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.Integer)
    content = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class UserAnswer(db.Model):
    __tablename__ = 'user_answer'
    id = db.Column(db.Integer, primary_key=True)
    story_question_id = db.Column(db.Integer, db.ForeignKey('story_question.id'), nullable=False)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogue.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Favorite(db.Model):
    __tablename__ = 'favorite'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    stories = Story.query.all()
    for story in stories:
        print(story.id, story.title, story.author, story.length)
# 注意：在user表中，password字段使用了VARCHAR(255)，实际应用中应使用更安全的加密方式存储密码。
# if __name__ == '__main__':
#     stories = [
#         Story(
#             title='冬天的花儿去哪儿了',
#             content='''宝贝，如果你家住在北方，冬天的时候树上和草地上都变得光秃秃的，那些绿绿的树叶和青草，还有五颜六色的花朵，都去哪了呢？我们和小驴托托一起寻找答案吧。
# 小驴托托非常非常喜欢花。可是到了冬天花儿都不见了。托托在雪地里到处找，花儿都去哪儿了呢？托托拎起洒水壶去浇花儿，想让花儿长出来，可是水很快就结成了冰。图图想问问鸟儿和松鼠，花儿都去哪儿了？可是松鼠一直在睡觉，鸟儿也都飞走了。托托着急的问妈妈：“花儿都去哪儿了？”妈妈回答：“花儿都钻进泥土里去休息了，他们在为明年春天的表演做准备呢。”
# 托托这下明白了。“好吧。在春天还没有到来之前，我先表演个冬天的节目吧。”图图高兴的说。''',
#             author='lucy',
#             length=1,
#             category_id=1  # 假设category_id是故事分类的ID
#         ),
#         Story(
#             title='你是我的小天使',
#             content='''听说，我是你的小天使。
# 洛洛听说自己是个小天使。
# 洛洛问：”妈妈，我从哪里来？”妈妈说：“洛洛，你从天上来。”
# 爸爸妈妈深爱着对方，他们想要一个孩子，于是爸爸在妈妈的身体里种下了一粒种子。
# 爸爸妈妈手拉手睡着了，睡梦中，他们飞上天空，遇见了一位仙女。仙女说：“来，挑一个小天使吧！”
# 小天使可真多呀。可是爸爸妈妈一眼，就发现了滑梯旁的那个小天使，它跑得真快呀，一笑，眼睛就眯了起来。
# 小天使跑了过来，爸爸妈妈的梦就醒了。
# 慢慢的，种子发了芽，变成了小宝宝儿，妈妈的肚子变得圆滚滚的。
# 9个月后，小宝宝洛洛出生了，长得和小天使一模一样，一笑，眼睛就眯了起来......
# ''',
#             author='shersty',
#             length=1,
#             category_id=1  # 假设category_id是故事分类的ID
#         )
#     ]
#     db.session.add(stories[0])
#     db.session.add(stories[1])
#     # 提交会话，保存数据到数据库
#     try:
#         db.session.commit()
#         print("Story added successfully.")
#     except Exception as e:
#         db.session.rollback()  # 如果出现异常，回滚会话
#         print(f"An error occurred: {e}")
