import json
import os
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
import paho.mqtt.client as mqtt
from werkzeug.utils import secure_filename
import requests
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
import logging

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

# MQTT服务器配置
MQTT_BROKER = '47.121.203.152'  # MQTT服务器地址
MQTT_PORT = 1883  # MQTT服务器端口
MQTT_TOPIC = '/sys/folotoy/d8132af12248/thing/command/call'  # 要发送消息的topic
ALLOWED_EXTENSIONS = set(['wav', 'txt'])
cosy_voice_url = 'http://43.240.0.168:6006/inference/stream'
prompt_text = "这里住着一只聪明的小动物，它的名字叫做小悟星。"


# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # 订阅topic
    client.subscribe(MQTT_TOPIC)


# MQTT消息接收函数
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))


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
        print(f"Audio file saved to {output_path}")

        # 加载 .wav 文件
        sound = AudioSegment.from_wav(output_path)
        # 导出为 .mp3 格式
        output_mp3_path = os.path.join(app.root_path, "tmp", "sounds", file_name + ".mp3")
        sound.export(output_mp3_path, format="mp3")
        print(f"cost time: {time.time() - start_time}")
        return output_mp3_path
    else:
        print("Error:", response.text)


# 创建MQTT客户端实例
client = mqtt.Client()
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
    client.publish(MQTT_TOPIC, payload=json.dumps(msg_1))
    return jsonify({'status': 'success', 'message': 'Story play command sent to MQTT.'}), 200


@app.route('/api/story/generate', methods=['GET'])
def get_audio_stream(story_id, voice_id, story_content):
    #     query = """宝贝，如果你家住在北方，冬天的时候树上和草地上都变得光秃秃的，那些绿绿的树叶和青草，还有五颜六色的花朵，都去哪了呢？我们和小驴托托一起寻找答案吧。
    # 小驴托托非常非常喜欢花。可是到了冬天花儿都不见了。托托在雪地里到处找，花儿都去哪儿了呢？托托拎起洒水壶去浇花儿，想让花儿长出来，可是水很快就结成了冰。图图想问问鸟儿和松鼠，花儿都去哪儿了？可是松鼠一直在睡觉，鸟儿也都飞走了。托托着急的问妈妈：“花儿都去哪儿了？”妈妈回答：“花儿都钻进泥土里去休息了，他们在为明年春天的表演做准备呢。”
    # 托托这下明白了。“好吧。在春天还没有到来之前，我先表演个冬天的节目吧。”图图高兴的说。"""
    voice = Voice.query.filter_by(id=voice_id).first()
    if voice is None:
        voice_desc = "tmp/sounds/xqf.wav"
    else:
        voice_desc = voice.voice_desc
    app.logger.info(f"准备生成 {voice_desc} - {story_content} 的故事")
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


@app.route('/api/story/audio/<int:story_id>/<int:voice_id>', methods=['GET'])
def play_story_by_id_and_voice(story_id, voice_id):
    # 使用filter_by查询，其中story_id和voice_id将从URL中自动转换为整数
    story_audio = StoryAudio.query.filter_by(story_id=story_id, voice_id=voice_id).all()
    # 如果没有找到故事音频，返回404状态码和错误消息
    if not story_audio:
        app.logger.info(f"没有找到{story_id}对应{voice_id}的音频文件，重新生成")
        story = Story.query.filter_by(id=story_id).first()
        story_content = story.content
        story_audio = get_audio_stream(story_id, voice_id, story_content)
        if story_audio:
            new_user = StoryAudio(story_id=story_id, voice_id=voice_id, audio_path=story_audio)
            # 添加到会话
            db.session.add(new_user)
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
                return jsonify({'success': True, 'story_audio': story_audio})
        return jsonify({'success': False, 'message': 'Generate failed'}), 404
    # 将查询结果转换为字典列表，然后返回
    story_audio_list = [
        {'id': audio.id, 'story_id': audio.story_id, 'voice_id': audio.voice_id, 'audio_path': audio.audio_path,
         'created': audio.created} for audio in story_audio]
    return jsonify({'success': True, 'story_audio': story_audio_list[0]["audio_path"]})


@app.route('/api/voice/record/', methods=['POST'])
def record_voice():
    # 访问JSON中的属性
    data = request.get_json()
    user_id = data.get('user_id')
    voice_tag = data.get('voice_tag')
    new_user = Voice(user_id=user_id, voice_desc=voice_tag)
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


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 6000), app)
    server.serve_forever()
