import json
import os
import re
import shutil
import threading
import time

from flask import Flask, request, jsonify, g, ctx
from flask_cors import CORS
import paho.mqtt.client as mqtt
from werkzeug.utils import secure_filename
import requests
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
import logging

from coze import create_session, create_chat, retrieve_chat, chat_list
from model import *

app = Flask(__name__)

CORS(app)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'tmp/sounds')
# 数据库相关配置
# 在扩展类实例化前加载配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + os.path.join(app.instance_path, 'flaskr.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
# 初始化扩展，传入程序实例 app
# db = SQLAlchemy(app)
db.init_app(app)
if not app.debug:
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    handler = logging.FileHandler('app.log')
    handler.setFormatter(logging.Formatter(log_format))
    app.logger.addHandler(handler)

from gevent import pywsgi

CLIENT_SN = "d8132af12248"
# MQTT服务器配置
MQTT_BROKER = '47.121.203.152'  # MQTT服务器地址
MQTT_PORT = 1883  # MQTT服务器端口
COMMAND_CALL_TOPIC = f'/sys/folotoy/{CLIENT_SN}/thing/command/call'  # 要发送消息的topic
EVENT_POST_TOPIC = f'/sys/folotoy/{CLIENT_SN}/thing/event/post'
AUDIO_PREFIX = "http://47.121.203.152:8082/"
ALLOWED_EXTENSIONS = set(['wav', 'txt'])
cosy_voice_url = 'http://43.240.0.168:6006/inference/stream'
prompt_text = "这里住着一只聪明的小动物，它的名字叫做小悟星。"
AUDIO_PATH = "/root/workspace/folotoy-server-self-hosting/audio"
# AUDIO_PATH = "/Users/shersty/Documents"
# 创建MQTT客户端实例
client = mqtt.Client()
global_message_id = 1


# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # 订阅topic
    client.subscribe(COMMAND_CALL_TOPIC)
    client.subscribe(EVENT_POST_TOPIC)


def extract_content(tag, text):
    pattern = re.compile(r'【' + re.escape(tag) + r'】[：:](.*?)\n')
    match = pattern.search(text)
    if match:
        return match.group(1)
    else:
        return "内容未找到"


def extract_content_from_tag(tag, text):
    pattern = re.compile(rf'【{tag}】[：:](.*)', re.DOTALL)
    match = pattern.search(text)
    if match:
        # 获取匹配的内容，并去除可能存在的首尾空白字符
        return match.group(1).strip()
    else:
        return "标签未找到，内容未获取"


def send_play_instruct(audio_path):
    global global_message_id
    audio_url = AUDIO_PREFIX
    if not os.path.dirname(audio_path) == AUDIO_PATH:
        app.logger.warning(f"音频文件{audio_path}没有存放在指定目录，先移动文件到指定目录")
        shutil.move(audio_path, os.path.join(AUDIO_PATH, os.path.basename(audio_path)))
    audio_url += os.path.basename(audio_path)
    msg = {"msgId": global_message_id, "identifier": "iwantplay", "inputParams": {"role": 2, "url": audio_url}}
    global_message_id += 1
    app.logger.info(f"发送播放指令:{json.dumps(msg)}")
    # 向MQTT服务器发送消息
    client.publish(COMMAND_CALL_TOPIC, payload=json.dumps(msg))


# MQTT消息接收函数
def on_message(client, userdata, msg):
    with app.app_context():
        new_dialogue = []
        if msg.topic == COMMAND_CALL_TOPIC:
            pass
        elif msg.topic == EVENT_POST_TOPIC:
            # 处理EVENT POST 主题的信息
            app.logger.info(msg.payload.decode())
            message_data = json.loads(msg.payload.decode())
            if message_data['identifier'] == 'recording_transcribed':
                recording_text = message_data["inputParams"]["recordingText"].encode('utf-8').decode()
                app.logger.info(recording_text)
                new_dialogue.append(Dialogue(user_id=1, role=2, content=recording_text, created=datetime.now()))
                # 这里是来自客户的语音输入，应该是回答问题的部分。
                if f"{CLIENT_SN}_session" in thread_results:
                    session_info = thread_results[f"{CLIENT_SN}_session"]
                else:
                    session_info = {
                        "sessionId": create_session(),
                        "story_id": 1,
                        "voice_id": 1,
                        "question_id": 0
                    }
                session_id = session_info["session_id"]
                story_id = session_info["story_id"]
                voice_id = session_info["voice_id"]
                question_id = session_info["question_id"]
                chat_data = create_chat(session_id, recording_text)
                state = retrieve_chat(session_id, chat_data["id"])
                while state != "completed":
                    print(f"{(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))} - chat_state: {state}")
                    state = retrieve_chat(session_id, chat_data["id"])
                    time.sleep(0.5)
                # 获取对话列表
                answer = chat_list(session_id, chat_data["id"])
                for data in answer:
                    if data["type"] == "answer":
                        coze_response = data["content"]
                        if "【主观评语】" in coze_response:
                            evaluate = extract_content('主观评语', coze_response)
                            new_dialogue.append(Dialogue(user_id=1, role=1, content=evaluate, created=datetime.now()))
                            if question_id < 2:
                                app.logger.info(f"是bot的回答，转为语音:{evaluate}")
                                # 问题数量 + 1
                                session_info["question_id"] += 1
                                thread_results[f"{CLIENT_SN}_session"] = session_info
                                evaluate_audio = get_audio_stream(story_id, voice_id, evaluate)
                                if question_id == 0:
                                    app.logger.info(f"第一个问题的评价，再拼接一个问题返回")
                                    # 第一个问题后边再拼接一个问题
                                    next_question = extract_content('问题', coze_response)
                                    new_dialogue.append(
                                        Dialogue(user_id=1, role=1, content=next_question, created=datetime.now()))
                                    next_question_audio = get_audio_stream(story_id, voice_id, next_question)
                                    # 加载第一段音频
                                    audio1 = AudioSegment.from_file(evaluate_audio)
                                    # 加载第二段音频
                                    audio2 = AudioSegment.from_file(next_question_audio)
                                    # 创建静音片段
                                    silence = AudioSegment.silent(duration=1500)
                                    # 将静音片段插入到两段音频之间
                                    combined_audio = audio1 + silence + audio2
                                    combined_audio_path = os.path.join(AUDIO_PATH,
                                                                       f"{story_id}_{voice_id}_{question_id}.mp3")
                                    combined_audio.export(combined_audio_path, format="mp3")
                                    send_play_instruct(combined_audio_path)
                                else:
                                    app.logger.info(f"第二个问题的评价，直接返回评价")
                                    send_play_instruct(evaluate_audio)
                                    # 三秒后自动组装并播放下一个故事
                                    timer = threading.Timer(3, lambda: play_next_story(story_id))
                                    timer.start()  # 启动计时器
                                new_dialogue.append(Dialogue(user_id=1, role=1,
                                                             content=extract_content_from_tag('客观评价',
                                                                                              coze_response),
                                                             created=datetime.now()))
                            else:
                                # 组装下一个故事
                                app.logger.info(f"播放下一个故事")
                                story_id = 1 if story_id == 2 else 2
                                play_story_by_id_and_voice(story_id, 1)
            elif message_data['identifier'] == 'voice_generated':
                if "voiceText" in message_data["inputParams"]:
                    voice_text = message_data["inputParams"]["voiceText"].encode('utf-8').decode()
                    app.logger.info(voice_text)
                    new_dialogue.append(Dialogue(user_id=1, role=1, content=voice_text, created=datetime.now()))
            add_dialogues(new_dialogue)


def play_next_story(story_id):
    with app.app_context():
        app.logger.info(f"播放下一个故事")
        story_id = 1 if story_id == 2 else 2
        play_story_by_id_and_voice(story_id, 1)


def save_audio_stream(story_id, voice_id, query, prompt_speech=None):
    # 构造请求数据
    start_time = time.time()
    data = {'query': query}
    if prompt_text is not None:
        data['prompt_text'] = prompt_text
    if prompt_speech is not None:
        data['prompt_speech'] = prompt_speech

    # json_data = json.dumps(data)

    # 发送 POST 请求
    response = requests.post(cosy_voice_url, json=data, stream=True)

    # 检查响应状态码是否为 200
    if response.status_code == 200:
        audio_data = b''
        # 读取并拼接音频流
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                audio_data += chunk
        file_name = f"{story_id}_{voice_id}_{int(time.time())}"
        # 将字节流转换为 NumPy 数组
        sample_rate = 22050  # 根据你的应用设定采样率
        audio_array = np.frombuffer(audio_data, dtype=np.float32)

        # 使用 soundfile 写入音频文件
        output_path = os.path.join(app.root_path, "tmp", "sounds", file_name + ".wav")
        sf.write(output_path, audio_array, sample_rate)
        app.logger.info(f"生成语音文件{output_path}")
        # 加载 .wav 文件
        sound = AudioSegment.from_wav(output_path)
        # TODO 修改此处保存位置为nginx的对应目录
        # 导出为 .mp3 格式
        output_mp3_path = os.path.join(AUDIO_PATH, file_name + ".mp3")
        app.logger.info(f"转换成mp3文件: {output_mp3_path}")
        sound.export(output_mp3_path, format="mp3")
        app.logger.info(f"花费时间: {time.time() - start_time}")
        return output_mp3_path
    else:
        print("Error:", response.text)


# 启动 MQTT 客户端
def start_mqtt_client():
    client.on_connect = on_connect
    client.on_message = on_message
    # 连接到MQTT服务器
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    # 启动MQTT客户端
    client.loop_start()


@app.route('/api/story/play', methods=['GET'])
def play_story():
    print("test")
    story_id = request.args.get('storyId', "")
    print(story_id)
    # 这里可以添加逻辑来处理请求参数等
    # 例如：story_id = request.args.get('story_id')
    msg_1 = {"msgId": 1, "identifier": "iwantplay",
             "inputParams": {"role": 2, "url": "http://47.121.203.152:8082/mcc.mp3"}}
    # 向MQTT服务器发送消息
    client.publish(COMMAND_CALL_TOPIC, payload=json.dumps(msg_1))
    return jsonify({'status': 'success', 'message': 'Story play command sent to MQTT.'}), 200


@app.route('/api/story/generate/<int:story_id>/<int:voice_id>/<string:story_content>', methods=['GET'])
def get_audio_stream(story_id, voice_id, story_content):
    #     query = """宝贝，如果你家住在北方，冬天的时候树上和草地上都变得光秃秃的，那些绿绿的树叶和青草，还有五颜六色的花朵，都去哪了呢？我们和小驴托托一起寻找答案吧。
    # 小驴托托非常非常喜欢花。可是到了冬天花儿都不见了。托托在雪地里到处找，花儿都去哪儿了呢？托托拎起洒水壶去浇花儿，想让花儿长出来，可是水很快就结成了冰。图图想问问鸟儿和松鼠，花儿都去哪儿了？可是松鼠一直在睡觉，鸟儿也都飞走了。托托着急的问妈妈：“花儿都去哪儿了？”妈妈回答：“花儿都钻进泥土里去休息了，他们在为明年春天的表演做准备呢。”
    # 托托这下明白了。“好吧。在春天还没有到来之前，我先表演个冬天的节目吧。”图图高兴的说。"""
    voice = Voice.query.filter_by(id=voice_id).first()
    if voice is None:
        voice_desc = "tmp/sounds/xqf.wav"
    else:
        voice_desc = voice.voice_desc
    app.logger.info(f"准备生成 {voice_desc} - {story_content} 的音频文件")
    return save_audio_stream(story_id, voice_id, story_content, voice_desc)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/api/upload/voice', methods=['POST'])
def upload_by_api():
    file = request.files['file']
    if file:
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': f'{file.filename} not valid.'})
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': True, 'message': f'File {filename} uploaded successfully.'})
    else:
        return jsonify({'success': False, 'message': 'No file found.'})


@app.route('/api/stories/all', methods=['GET'])
def query_all_story():
    stories = Story.query.all()
    # 将查询结果转换为列表
    story_list = [{'id': story.id, 'title': story.title, 'content': story.content} for story in stories]
    return jsonify({'success': True, 'stories': story_list})


# local_data = threading.local()
thread_results = {}


@app.route('/api/story/audio/<int:story_id>/<int:user_id>', methods=['GET'])
def play_story_by_id_and_voice(story_id, user_id):
    new_dialogues = []
    # 获取当前user_id对应的voice_id
    voice = Voice.query.filter_by(user_id=user_id, is_checked=True).first()
    voice_id = voice.id
    app.logger.info(f"用户{user_id}选中的语音为{voice_id} - {voice.voice_desc}")
    story = Story.query.filter_by(id=story_id).first()
    story_content = story.content
    # 复制当前应用上下文
    thread1 = threading.Thread(target=get_story_audio_by_id_and_voice,
                               kwargs={'story_id': story_id, 'voice_id': voice_id, 'story_content': story_content})
    thread1.start()
    thread2 = threading.Thread(target=get_story_question_by_id_and_voice,
                               kwargs={'story_id': story_id, 'voice_id': voice_id})
    thread2.start()
    thread1.join()
    thread2.join()
    # 加载第一段音频
    audio1 = AudioSegment.from_file(thread_results[f"{story_id}_{voice_id}_story_audio"])
    # 加载第二段音频
    question_audio = thread_results[f"{story_id}_{voice_id}_question_audio"]
    audio2 = AudioSegment.from_file(question_audio["path"])
    # 创建静音片段
    silence = AudioSegment.silent(duration=1500)
    # 将静音片段插入到两段音频之间
    combined_audio = audio1 + silence + audio2
    combined_audio_path = os.path.join(AUDIO_PATH, f"{story_id}_{voice_id}.mp3")
    combined_audio.export(combined_audio_path, format="mp3")
    send_play_instruct(combined_audio_path)
    new_dialogues.append(Dialogue(user_id=1, role=1, content=story_content, created=datetime.now()))
    new_dialogues.append(Dialogue(user_id=1, role=1, content=question_audio["content"], created=datetime.now()))
    add_dialogues(new_dialogues)
    return jsonify({'status': 'success', 'message': 'Story play command sent to MQTT.'}), 200


def add_dialogues(new_dialogues):
    with app.app_context():
        if new_dialogues:
            # 添加到会话
            db.session.add_all(new_dialogues)
            try:
                # 提交会话
                db.session.commit()
                app.logger.info(f"对话提交成功！")
            except Exception as e:
                # 如果发生错误，回滚会话
                db.session.rollback()
                app.logger.error(e)
                app.logger.info(f"对话提交数据库失败")


def get_story_audio_by_id_and_voice(story_id, voice_id, story_content):
    with app.app_context():
        # 使用filter_by查询，其中story_id和voice_id将从URL中自动转换为整数
        story_audio = StoryAudio.query.filter_by(story_id=story_id, voice_id=voice_id).first()
        # 如果没有找到故事音频，返回404状态码和错误消息
        if not story_audio:
            app.logger.info(f"没有找到{story_id}对应{voice_id}的音频文件，重新生成")
            story_audio = get_audio_stream(story_id, voice_id, story_content)
            if story_audio:
                new_story_audio = StoryAudio(story_id=story_id, voice_id=voice_id, audio_path=story_audio)
                # 添加到会话
                db.session.add(new_story_audio)
                try:
                    # 提交会话
                    db.session.commit()
                    app.logger.info(f"故事生成成功！")
                except Exception as e:
                    # 如果发生错误，回滚会话
                    db.session.rollback()
                    app.logger.error(e)
                    app.logger.info(f"提交数据库失败")
                finally:
                    thread_results[f"{story_id}_{voice_id}_story_audio"] = story_audio
                    # g.story_audio = story_audio
            else:
                thread_results[f"{story_id}_{voice_id}_story_audio"] = ""
        else:
            thread_results[f"{story_id}_{voice_id}_story_audio"] = story_audio.audio_path


def get_story_question_by_id_and_voice(story_id, voice_id):
    with app.app_context():
        app.logger.info(f"生成故事对应的问题")
        story = Story.query.filter_by(id=story_id).first()
        if story.need_question:
            content = story.content
            # 请求coze获取故事对应的问题
            session_id = create_session()
            thread_results[f"{CLIENT_SN}_session"] = {
                "session_id": session_id,
                "story_id": story_id,
                "voice_id": voice_id,
                "question_id": 0
            }
            chat_data = create_chat(session_id, content)
            state = retrieve_chat(session_id, chat_data["id"])
            while state != "completed":
                print(f"{(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))} - chat_state: {state}")
                state = retrieve_chat(session_id, chat_data["id"])
                time.sleep(0.5)
            # 获取对话列表
            answer = chat_list(session_id, chat_data["id"])
            for data in answer:
                if data["type"] == "answer":
                    question = data["content"].split("：")[-1]
                    app.logger.info(f"是bot的回答，转为语音:{question}")
                    question_audio = get_audio_stream(story_id, voice_id, question)
                    thread_results[f"{story_id}_{voice_id}_question_audio"] = {
                        "path": question_audio,
                        "content": question
                    }
                    break
        else:
            app.logger.info(f"不用提问题，嵌入小悟的广告词")
            story = Story.query.filter_by(id=666).first()
            question_audio = get_audio_stream(666, voice_id, story.content)
            thread_results[f"{story_id}_{voice_id}_question_audio"] = {
                "path": question_audio,
                "content": story.content
            }


@app.route('/api/voice/record/', methods=['POST'])
def record_voice():
    # 访问JSON中的属性
    data = request.get_json()
    app.logger.info(data)
    user_id = data.get('user_id')
    voice_tag = data.get('voice_tag')
    voice_name = data.get('voice_name')
    new_user = Voice(user_id=user_id, voice_desc=voice_name, voice_tag=voice_tag)
    # 添加到会话
    db.session.add(new_user)
    try:
        # 提交会话
        db.session.commit()
        app.logger.info(f"音色记录成功")
    except Exception as e:
        # 如果发生错误，回滚会话
        db.session.rollback()
        app.logger.error(e)
        app.logger.info(f"提交数据库失败")
        return jsonify({'success': False, 'message': 'Voice record failed'}), 404
    return jsonify({'success': True, 'voice_desc': voice_tag})


@app.route('/api/voice/all', methods=['GET'])
def get_voice_list():
    voices = Voice.query.all()
    exclude_id = 666
    # 将查询结果转换为列表
    voice_list = [{'id': voice.id, 'userId': voice.user_id, 'voiceDesc': voice.voice_tag, "created": voice.created,
                   "isChecked": voice.is_checked} for voice in voices if voice.id != exclude_id]
    return jsonify({'success': True, 'voiceBeans': voice_list})


@app.route('/api/dialogue/all', methods=['GET'])
def get_dialogue_list():
    dialogs = Dialogue.query.all()
    dialogue_list = [{'type': dialog.role, 'content': dialog.content, 'created': dialog.created}
                     for dialog in dialogs]
    return jsonify({'success': True, 'dialogueList': dialogue_list})


@app.route('/api/voice/update/', methods=['POST'])
def update_voice_checked_state():
    # 从POST请求中获取JSON数据
    data = request.get_json()
    voice_id = data.get('voice_id')
    is_checked = data.get('is_checked')
    user_id = data.get('user_id')
    # 检查必要的参数是否存在
    if not voice_id or not isinstance(is_checked, bool) or not user_id:
        return jsonify({'error': '缺少必要的参数'}), 400
    # 锁定同一user_id下的所有voice记录
    voices = Voice.query.filter_by(user_id=user_id).with_for_update().all()
    # 遍历这些记录，更新选中状态
    # 只有指定voice_id的记录会设置为is_checked，其他都设置为False
    for voice in voices:
        if voice.id == voice_id:
            voice.is_checked = is_checked
        else:
            voice.is_checked = False
    # 提交事务
    try:
        db.session.commit()
        return jsonify({'message': '选中状态更新成功'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '更新失败'}), 500


@app.route('/api/voice/delete/', methods=['POST'])
def delete_voice():
    data = request.get_json()
    voice_id = data.get('voice_id')
    voice_to_delete = Voice.query.filter_by(id=voice_id).first()
    if voice_to_delete:
        # 删除找到的对象
        db.session.delete(voice_to_delete)
        # 提交会话中的更改
        db.session.commit()
        # 删除后，查询剩余的Voice列表
        remaining_voices = Voice.query.all()
        voice_list = [{'id': voice.id, 'userId': voice.user_id, 'voiceDesc': voice.voice_tag, "created": voice.created,
                       "isChecked": voice.is_checked} for voice in remaining_voices]
        return jsonify(
            {'success': True, 'voiceBeans': voice_list}), 200
    else:
        # 如果没有找到对象，返回错误消息
        return jsonify({'success': False}), 404


@app.route('/api/story/add', methods=['POST'])
def add_story():
    # 获取JSON数据
    data = request.get_json()
    # 创建Story实例
    new_story = Story(
        category_id=data['category_id'],
        title=data['title'],
        content=data['content'],
        author=data.get('author'),  # 如果没有提供作者，则为None
        length=len(data['content']),  # 假设长度是内容的长度
        need_question=data.get('need_question')
    )
    # 添加到session并提交
    db.session.add(new_story)
    db.session.commit()
    # 返回响应
    return jsonify({"message": "Story added successfully", "story_id": new_story.id}), 201


if __name__ == '__main__':
    # 启动 MQTT 客户端线程
    mqtt_thread = threading.Thread(target=start_mqtt_client)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    server = pywsgi.WSGIServer(('0.0.0.0', 6000), app)
    server.serve_forever()
