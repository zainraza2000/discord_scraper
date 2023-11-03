import requests
import json
import os
import time
from datetime import datetime
import os
import openai
import tiktoken

tokenizer = tiktoken.get_encoding('cl100k_base')
openai.organization = os.env('OPENAI_ORG')
openai.api_key = os.env('OPENAI_KEY')

last_message_data = ''
end_message = ''
spl = 'IAMTHESPLITTER'


def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)


def get_completion(prompt):
    print('Prompting started...')
    print('tokens consumed: ' + str(tiktoken_len(prompt)))
    response = openai.ChatCompletion.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    print('Prompting ended...')
    return response.choices[0].message.content


def get_normalised_text(prompt, content):
    print("Normalising text...")
    prompt_length = tiktoken_len(prompt)
    content_length = tiktoken_len(content)
    total_tokens = content_length + prompt_length
    max_tokens = 3850 - prompt_length
    if total_tokens <= 4000:
        return [content]
    else:
        init_str = ''
        str_arr = []
        messages = content.split(spl)
        for message in messages:
            if (tiktoken_len(init_str+message) > max_tokens):
                str_arr.append(init_str)
                init_str = ''
            else:
                init_str += message + "\n\n"
        if (len(init_str) > 0):
            str_arr.append(init_str)
        return str_arr


def get_normalised_json(prompt, json_str):
    prompt_length = tiktoken_len(prompt)
    json_arr = json.loads(json_str)
    content_length = tiktoken_len(json_str)
    total_tokens = content_length + prompt_length
    max_tokens = 3850 - prompt_length
    if total_tokens <= 4000:
        return [json_str]
    else:
        normalised_arr = []
        parsed_json = []
        for obj in json_arr:
            if (tiktoken_len(json.dumps(parsed_json)) > max_tokens):
                normalised_arr.append(json.dumps(parsed_json))
            parsed_json.append(obj)
        return normalised_arr


def create_txt(file_name, all_messages):
    content = ''
    for message in all_messages:
        content += message['username'] + '--//--' + message['content'] + spl
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(content)


def retrieve_messages(channel_id, token, last_message, start_date, end_date):
    headers = {'Authorization': token}
    base_url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    params = {'limit': 100}

    if last_message:
        params['before'] = last_message

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Request Exception: {err}")
        return None

    try:
        json_data = response.json()
    except json.JSONDecodeError as err:
        print(f"JSON Decode Error: {err}")
        return None

    filtered_messages = []

    if len(json_data):
        global end_message
        end_message = json_data[-1].get('id')
        global last_message_data
        last_message_data = json_data[-1].get('timestamp')
        last_message_data = datetime.fromisoformat(last_message_data[:-6])

    for message in json_data:
        timestamp = message.get('timestamp')
        if timestamp:
            message_date = datetime.fromisoformat(timestamp[:-6])
            if start_date <= message_date <= end_date:
                filtered_messages.append(message)

    return filtered_messages


def text_prompt(prompt, messages):
    responses = []
    normalized_text = get_normalised_text(prompt, messages)
    for message in normalized_text:
        print(tiktoken_len(message))
        response = get_completion(prompt + ':\n'+message)
        last_index = len(responses) - 1
        if len(responses) > 0:
            length = tiktoken_len(prompt + response + responses[last_index])
            if length < 4000:
                print('Merging responses...')
                responses[last_index] = merge_json_arrays_as_string(
                    responses[last_index], response)
            else:
                responses.append(response)
        else:
            responses.append(response)
    return responses


def json_prompt(prompt, questions_json):
    responses = []
    i = 1
    for questions in questions_json:
        for normalised_question in get_normalised_json(prompt, questions):
            with open(f'prompt{i}.txt', 'w', encoding='utf-8') as file:
                file.write(prompt + ':\n' + normalised_question)
            i += 1
            # responses.append(get_completion(
            #     prompt + ':\n' + normalised_question))
    return responses


def merge_json_arrays_as_string(arr_1, arr_2):
    try:
        response = []
        obj_1 = json.loads(arr_1)
        obj_2 = json.loads(arr_2)
        for obj in obj_1:
            response.append(obj)
        for obj in obj_2:
            response.append(obj)
        return json.dumps(response)
    except:
        with open('error.txt', 'w', encoding='utf-8') as file:
            file.write(arr_1)


def merge_json_arrays(json_arrs):
    response = []
    for json_arr in json_arrs:
        arr = json.loads(json_arr)
        for obj in arr:
            response.append(obj)
    return response


with open('config.json') as f:
    config = json.load(f)

token = config.get("token")
channel_id = config.get("channelId")
is_prompt = config.get("isPrompt")
last_message_file = 'last_message.json'
start_date = datetime.fromisoformat(config.get("startDate") + 'T00:00:00')
end_date = datetime.fromisoformat(config.get("endDate") + 'T23:59:59')


i = 0
all_messages = []


if os.path.exists(last_message_file):
    with open(last_message_file) as f:
        data = json.load(f)
        last_message = data.get('last_message', '')
else:
    last_message = ''


############################################################################################################################


while True:
    json_data = retrieve_messages(
        channel_id=channel_id, token=token, last_message=end_message,
        start_date=start_date, end_date=end_date
    )

    if json_data is None:
        print("Error retrieving messages. Exiting.")
        break

    if len(json_data) == 0 and end_date > last_message_data:
        break

    if len(json_data) and json_data[-1]:
        date_time = json_data[-1].get('timestamp')
        message_date = datetime.fromisoformat(date_time[:-6])
        if start_date > message_date:
            break

    for value in json_data:
        username = value['author']['username']
        content = value.get('content', 'No content')
        attachments = value.get('attachments', [])
        timestamp = value.get('timestamp', None)
        last_message = value['id']

        all_messages.append(
            {'username': username, 'timestamp': timestamp, 'content': content, 'attachments': attachments})

    i += 1

    time.sleep(2)

file_name = f'messages{config.get("startDate")}_{config.get("endDate")}'

with open(file_name+'.json', 'a') as f:
    json.dump(all_messages, f, indent=2)
file_name = file_name.replace('.json', '.txt')
create_txt(file_name+'.txt', all_messages)
if is_prompt:
    with open(file_name+'.txt', 'r', encoding='utf-8') as file:
        messages = file.read()
    init_prompt = 'Examine the given chat logs. Identify direct questions asked by users. Extract and summarize each question. Provide just the json code, no extra text! Structure the information in parsable JSON format with the fields: "user", "exact question", and "summarized question".'
    final_prompt = 'Analyze the provided JSON data of user questions. Identify and group similar questions based on the "summarized question" field. For each group of similar questions, combine user names and their exact questions. Provide just the json code, no extra text! Format the output in parsable JSON with the fields: "users", "exact questions", and "summarized question".'
    questions_json = text_prompt(init_prompt, messages)
    merged_arr = merge_json_arrays(questions_json)
    with open(file_name+'_questions'+'.json', 'a') as f:
        json.dump(merged_arr, f, indent=2)
