from flask import Flask, jsonify, request
import random
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# 全局变量
stop_event = threading.Event()
log_queue = queue.Queue()
thread_pool = ThreadPoolExecutor(max_workers=10)

diastolic_pressures = []
systolic_pressures = []
timestamps = []
statuses = []
heart_rates = []
heart_rate_statuses = []
temperatures = []
temperature_statuses = []
calories_burned = []

def generate_data():
    while not stop_event.is_set():
        try:
            sampling_period = float(request.json.get('sampling_period', 1))

            if sampling_period <= 0:
                raise ValueError("采样周期必须大于0")

            # 根据概率分布生成血压状态
            rand_val = random.random()
            if rand_val < 0.26:
                status = "高血压"
            elif rand_val < 0.91:
                status = "正常血压"
            else:
                status = "低血压"

            # 根据状态生成血压值
            if status == "高血压":
                systolic_pressure = random.uniform(140, 200)  # 高血压收缩压范围
                diastolic_pressure = random.uniform(90, 120)  # 高血压舒张压范围
            elif status == "正常血压":
                systolic_pressure = random.uniform(90, 139)  # 正常血压收缩压范围
                diastolic_pressure = random.uniform(60, 89)  # 正常血压舒张压范围
            else:
                systolic_pressure = random.uniform(70, 89)  # 低血压收缩压范围
                diastolic_pressure = random.uniform(40, 59)  # 低血压舒张压范围

            # 调整数据点更接近 y = 2/3x
            diastolic_pressure = systolic_pressure * 2 / 3 + random.gauss(0, 5)

            # 确保生成的压力值在合理的范围内
            systolic_pressure = max(0, systolic_pressure)
            diastolic_pressure = max(0, diastolic_pressure)

            diastolic_pressures.append(diastolic_pressure)
            systolic_pressures.append(systolic_pressure)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            timestamps.append(timestamp)

            statuses.append(status)  # 将状态添加到列表中

            # 生成心率数据
            heart_rate = random.randint(40, 120)  # 心率范围40-120
            heart_rate_status = determine_heart_rate_status(heart_rate)

            heart_rates.append(heart_rate)
            heart_rate_statuses.append(heart_rate_status)

            # 生成体温数据
            temperature = round(random.uniform(35.5, 38.0), 1)  # 体温范围35.5-38.0
            temperature_status = determine_temperature_status(temperature)

            temperatures.append(temperature)
            temperature_statuses.append(temperature_status)

            # 生成卡路里消耗数据
            calories_burned = random.uniform(0, 500)  # 卡路里消耗范围0-500
            calories_burned.append(calories_burned)

            log_message = (f"时间: {timestamp} - "
                           f"舒张压: {diastolic_pressure:.2f}, 收缩压: {systolic_pressure:.2f}, "
                           f"心率: {heart_rate}, 心率状态: {heart_rate_status}, "
                           f"体温: {temperature}, 体温状态: {temperature_status}, "
                           f"卡路里消耗: {calories_burned:.2f}, "
                           f"血压状态: {status}\n")
            log_queue.put(log_message)

            time.sleep(sampling_period)
        except ValueError as e:
            error_message = f"输入错误: {e}\n"
            log_queue.put(error_message)
            break

def determine_heart_rate_status(heart_rate):
    if 60 <= heart_rate <= 100:
        return "正常心率"
    elif heart_rate < 60:
        return "心动过缓"
    else:
        return "心动过速"

def determine_temperature_status(temperature):
    if 36.1 <= temperature <= 37.2:
        return "正常体温"
    elif temperature < 36.1:
        return "体温过低"
    else:
        return "体温过高"

@app.route('/start_logging', methods=['POST'])
def start_logging():
    global stop_event, thread_pool
    stop_event.clear()
    sampling_period = float(request.json.get('sampling_period', 1))
    num_threads = int(request.json.get('num_threads', 1))
    for _ in range(num_threads):
        thread_pool.submit(generate_data)
    return jsonify({"status": "started"})

@app.route('/stop_logging', methods=['POST'])
def stop_logging():
    global stop_event
    stop_event.set()
    return jsonify({"status": "stopped"})

@app.route('/get_log', methods=['GET'])
def get_log():
    log_messages = []
    try:
        while True:
            log_messages.append(log_queue.get_nowait())
    except queue.Empty:
        pass
    return jsonify({"log": log_messages})

@app.route('/get_data', methods=['GET'])
def get_data():
    data = {
        'diastolic_pressures': diastolic_pressures,
        'systolic_pressures': systolic_pressures,
        'timestamps': timestamps,
        'statuses': statuses,
        'heart_rates': heart_rates,
        'heart_rate_statuses': heart_rate_statuses,
        'temperatures': temperatures,
        'temperature_statuses': temperature_statuses,
        'calories_burned': calories_burned
    }
    return jsonify(data)

@app.route('/clear_data', methods=['POST'])
def clear_data():
    global diastolic_pressures, systolic_pressures, timestamps, statuses, heart_rates, heart_rate_statuses, temperatures, temperature_statuses, calories_burned
    diastolic_pressures.clear()
    systolic_pressures.clear()
    timestamps.clear()
    statuses.clear()
    heart_rates.clear()
    heart_rate_statuses.clear()
    temperatures.clear()
    temperature_statuses.clear()
    calories_burned.clear()
    return jsonify({"status": "cleared"})

@app.route('/plot_data', methods=['GET'])
def plot_data():
    plt.figure(figsize=(10, 6))

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    colors = []
    for systolic, diastolic in zip(systolic_pressures, diastolic_pressures):
        if systolic >= 140 or diastolic >= 90:
            colors.append('red')  # 高血压
        elif systolic < 90 or diastolic < 60:
            colors.append('black')  # 低血压
        else:
            colors.append('blue')  # 正常血压
    plt.scatter(diastolic_pressures, systolic_pressures, c=colors, label='生成的数据点')
    
    # 绘制 y = 2/3x 的基准线
    x = range(0, 200)
    y = [2/3 * xi for xi in x]
    plt.plot(y, x, color='red', label='y = 2/3x')
    plt.xlabel('收缩压')
    plt.ylabel('舒张压')
    plt.title('血压数据点分布')
    plt.legend()
    plt.grid(True)

    # 将图像保存到内存中
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # 将图像编码为 base64
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    # 绘制心率数据
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, heart_rates, label='心率')
    plt.axhline(y=60, color='red', linestyle='--', label='正常心率下限')
    plt.axhline(y=100, color='red', linestyle='--', label='正常心率上限')
    plt.xlabel('时间')
    plt.ylabel('心率 (次/分钟)')
    plt.title('心率变化')
    plt.legend()
    plt.grid(True)

    # 将图像保存到内存中
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # 将图像编码为 base64
    heart_rate_plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    # 绘制体温数据
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, temperatures, label='体温')
    plt.axhline(y=36.1, color='red', linestyle='--', label='正常体温下限')
    plt.axhline(y=37.2, color='red', linestyle='--', label='正常体温上限')
    plt.xlabel('时间')
    plt.ylabel('体温 (°C)')
    plt.title('体温变化')
    plt.legend()
    plt.grid(True)

    # 将图像保存到内存中
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # 将图像编码为 base64
    temperature_plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    return jsonify({
        'plot_url': plot_url,
        'heart_rate_plot_url': heart_rate_plot_url,
        'temperature_plot_url': temperature_plot_url
    })

if __name__ == '__main__':
    app.run(debug=True)