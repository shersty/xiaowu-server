import json
import time

import requests

headers = {
    'Authorization': 'Bearer pat_ZwnwnwhUdtI1zMZZIO5TlcENH3f0rS8k5DFB7I2oCEHGYtisfdvXtNIXgPQLdfW4',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Host': 'api.coze.cn',
    'Connection': 'keep-alive'
}
bot_id = "7397417578425532468"
user_id = "29032201862555"


def create_session():
    """
    创建会话
    :return:
    """
    url = "https://api.coze.cn/v1/conversation/create"
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        answer = json.loads(response.text)
        if answer["code"] == 0:
            return answer["data"]["id"]
        print(f"coze bot Request failed with status code {answer['code']}")
    else:
        print(f"Request failed with status code {response.status_code}")


def retrieve_session(conversation_id):
    """
    查看会话信息
    :param conversation_id:
    :return:
    """
    url = "https://api.coze.cn/v1/conversation/retrieve?conversationId={}".format(conversation_id)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        answer = json.loads(response.text)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")


def create_message(conversation_id, message):
    """
    创建消息
    :param conversation_id:
    :param message:
    :return:
    """
    url = " https://api.coze.cn/v1/conversation/message/create?conversation_id=" + conversation_id
    data = {
        "role": "user",
        "content": message,
        "content_type": "text"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        answer = json.loads(response.text)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")


def list_message(conversation_id):
    url = " https://api.coze.cn/v1/conversation/message/list?conversation_id=" + conversation_id
    response = requests.get(url, headers=headers, params={'conversation_id': conversation_id})
    if response.status_code == 200:
        answer = json.loads(response.text)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")


def retrieve_message(conversation_id, message_id):
    url = "https://api.coze.cn/v1/conversation/message/retrieve"
    response = requests.get(url, headers=headers, params={'conversation_id': conversation_id, 'message_id': message_id})
    if response.status_code == 200:
        answer = json.loads(response.text)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")


def create_chat(conversation_id, query):
    url = 'https://api.coze.cn/v3/chat?conversation_id={}'.format(conversation_id)
    data = {
        "bot_id": bot_id,
        "user_id": user_id,
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": query,
                "content_type": "text"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)
    # # 遍历流式响应
    # for chunk in response.iter_content():
    #     if chunk:  # 确保不是空行
    #         # decoded_line = chunk.decode('utf-8')  # 解码行数据
    #         print(chunk)  # 打印或处理数据
    if response.status_code == 200:
        answer = json.loads(response.text)
        if answer["code"] == 0:
            return answer["data"]
        print(f"coze bot Request failed with status code {answer['code']}")
    else:
        print(f"Request failed with status code {response.status_code}")


def retrieve_chat(conversation_id, chat_id):
    url = 'https://api.coze.cn/v3/chat/retrieve'
    response = requests.get(url, headers=headers, params={'conversation_id': conversation_id, 'chat_id': chat_id})
    if response.status_code == 200:
        answer = json.loads(response.text)
        if answer["code"] == 0:
            return answer["data"]["status"]
        print(f"coze bot Request failed with status code {answer['code']}")
    else:
        print(f"Request failed with status code {response.status_code}")


def chat_list(conversation_id, chat_id):
    url = " https://api.coze.cn/v3/chat/message/list"
    response = requests.get(url, headers=headers, params={'conversation_id': conversation_id, 'chat_id': chat_id})
    if response.status_code == 200:
        answer = json.loads(response.text)
        print(answer)
        if answer["code"] == 0:
            return answer["data"]
        print(f"coze bot Request failed with status code {answer['code']}")
    else:
        print(f"Request failed with status code {response.status_code}")


if __name__ == '__main__':
    # answer = chat_list("7399543335083343922", "7399543335083393074")
    # for data in answer["data"]:
    #     print(data)

    # 创建一个会话
    session_id = create_session()
    # session_id = "7404406791984988172"
    print(f"{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} - session_id: {session_id}")
    # 在session中创建一个对话
    # chat_data = create_chat(session_id, "在一个遥远的森林里，有一只聪明勇敢的小兔子，它和朋友们快乐地生活。一天，森林里来了一只贪婪的狼，想要占领这片土地。小兔子想出了一个计划，它带领大家挖了一个大陷阱，成功地捉住了狼。从此，森林恢复了和平，所有动物都过上了幸福的生活。")
    chat_data = create_chat(session_id, "小兔子很聪明")
    print(f"{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} - chat_data: {chat_data}")
    # 查询对话状态
    state = retrieve_chat(session_id, chat_data["id"])
    while state != "completed":
        print(f"{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} - chat_state: {state}")
        state = retrieve_chat(session_id, chat_data["id"])
        time.sleep(0.5)
    # 获取对话列表
    answer = chat_list(session_id, chat_data["id"])
    for data in answer:
        if data["type"] == "answer":
            print(f"是bot的回答，转为语音")
            content = data["content"]
            # save_audio_stream(content, "xyy.wav", output_file=f"{session_id}_{data['id']}.wav")
        print(data)
