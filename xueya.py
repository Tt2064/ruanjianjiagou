import tkinter as tk
from tkinter import ttk
import random
import math
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

class BloodPressureMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("参数设置和日志界面")
        self.root.geometry("800x600")

        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.thread_pool = ThreadPoolExecutor(max_workers=10)  # 线程池，最多同时运行10个线程

        self.diastolic_pressures = []
        self.systolic_pressures = []
        self.timestamps = []
        self.statuses = []  # 新增列表用于存储血压状态

        self.create_widgets()
        self.setup_layout()
        self.process_queue()

    def create_widgets(self):
        # 创建参数设置板块
        self.param_frame_left = ttk.LabelFrame(self.root, text="参数设置 (左)")
        self.param_frame_left.grid(row=0, column=0, padx=20, pady=0, sticky="nsew")

        self.param_label6 = ttk.Label(self.param_frame_left, text="采样周期 (秒):")
        self.param_label6.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.param_entry6 = ttk.Entry(self.param_frame_left)
        self.param_entry6.grid(row=0, column=1, padx=10, pady=10)

        self.param_label7 = ttk.Label(self.param_frame_left, text="线程数量:")
        self.param_label7.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.param_spinbox7 = ttk.Spinbox(self.param_frame_left, from_=1, to=10, increment=1, width=5)
        self.param_spinbox7.grid(row=1, column=1, padx=10, pady=10)

        self.param_label1 = ttk.Label(self.param_frame_left, text="舒张压均值:")
        self.param_label1.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.param_entry1 = ttk.Entry(self.param_frame_left, state=tk.DISABLED)
        self.param_entry1.grid(row=2, column=1, padx=10, pady=10)

        self.param_frame_right = ttk.LabelFrame(self.root, text="参数设置 (右)")
        self.param_frame_right.grid(row=0, column=1, padx=20, pady=0, sticky="nsew")

        self.param_label2 = ttk.Label(self.param_frame_right, text="舒张压方差:")
        self.param_label2.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.param_entry2 = ttk.Entry(self.param_frame_right, state=tk.DISABLED)
        self.param_entry2.grid(row=0, column=1, padx=10, pady=10)

        self.param_label3 = ttk.Label(self.param_frame_right, text="收缩压均值:")
        self.param_label3.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.param_entry3 = ttk.Entry(self.param_frame_right, state=tk.DISABLED)
        self.param_entry3.grid(row=1, column=1, padx=10, pady=10)

        self.param_label4 = ttk.Label(self.param_frame_right, text="收缩压方差:")
        self.param_label4.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.param_entry4 = ttk.Entry(self.param_frame_right, state=tk.DISABLED)
        self.param_entry4.grid(row=2, column=1, padx=10, pady=10)

        # 创建日志板块
        self.log_frame = ttk.LabelFrame(self.root, text="日志")
        self.log_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 创建开始和停止按钮
        self.start_button = ttk.Button(self.root, text="开始", command=self.start_logging)
        self.start_button.grid(row=2, column=0, padx=10, pady=10, sticky="e")

        self.stop_button = ttk.Button(self.root, text="停止", command=self.stop_logging, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # 创建清理日志按钮
        self.clear_button = ttk.Button(self.root, text="清理日志", command=self.clear_log)
        self.clear_button.grid(row=2, column=2, padx=10, pady=10, sticky="w")

    def setup_layout(self):
        self.root.grid_rowconfigure(0, weight=2)  # 参数设置区域权重更大
        self.root.grid_rowconfigure(1, weight=1)  # 日志区域权重更小
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        style = ttk.Style()
        style.configure('TButton', foreground='blue')
        style.configure('TLabel', foreground='black', font=('Arial', 10))
        style.configure('TEntry', foreground='black', font=('Arial', 10))

    def generate_random_value(self, mean, variance):
        std_dev = math.sqrt(variance)
        return random.gauss(mean, std_dev)

    def determine_blood_pressure_status(self, systolic, diastolic):
        if systolic < 120 and diastolic < 80:
            return "正常血压"
        elif 120 <= systolic < 130 and diastolic < 80:
            return "高血压前期"
        elif (130 <= systolic < 140) or (80 <= diastolic < 90):
            return "高血压 1级"
        elif systolic >= 140 or diastolic >= 90:
            return "高血压 2级"
        elif systolic >= 180 or diastolic >= 120:
            return "高血压危象"
        else:
            return "未知状态"

    def start_logging(self):
        try:
            sampling_period = float(self.param_entry6.get())
            if sampling_period <= 0:
                raise ValueError("采样周期必须大于0")
        except ValueError as e:
            self.log_queue.put(f"输入错误: {e}\n")
            return

        self.stop_event.clear()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # 获取用户选择的线程数量
        num_threads = int(self.param_spinbox7.get())

        # 启动指定数量的线程
        for _ in range(num_threads):
            self.thread_pool.submit(self.generate_data)

    def stop_logging(self):
        self.stop_event.set()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        # 计算均值和方差
        if self.diastolic_pressures:
            diastolic_mean = sum(self.diastolic_pressures) / len(self.diastolic_pressures)
            diastolic_variance = sum((x - diastolic_mean) ** 2 for x in self.diastolic_pressures) / len(self.diastolic_pressures)
            self.param_entry1.config(state=tk.NORMAL)
            self.param_entry1.delete(0, tk.END)
            self.param_entry1.insert(0, f"{diastolic_mean:.2f}")
            self.param_entry1.config(state=tk.DISABLED)

        if self.systolic_pressures:
            systolic_mean = sum(self.systolic_pressures) / len(self.systolic_pressures)
            systolic_variance = sum((x - systolic_mean) ** 2 for x in self.systolic_pressures) / len(self.systolic_pressures)
            self.param_entry3.config(state=tk.NORMAL)
            self.param_entry3.delete(0, tk.END)
            self.param_entry3.insert(0, f"{systolic_mean:.2f}")
            self.param_entry3.config(state=tk.DISABLED)

            self.param_entry2.config(state=tk.NORMAL)
            self.param_entry2.delete(0, tk.END)
            self.param_entry2.insert(0, f"{diastolic_variance:.2f}")
            self.param_entry2.config(state=tk.DISABLED)

            self.param_entry4.config(state=tk.NORMAL)
            self.param_entry4.delete(0, tk.END)
            self.param_entry4.insert(0, f"{systolic_variance:.2f}")
            self.param_entry4.config(state=tk.DISABLED)

        # 保存数据到CSV文件
        self.save_to_csv()

    def generate_data(self):
        while not self.stop_event.is_set():
            try:
                sampling_period = float(self.param_entry6.get())

                if sampling_period <= 0:
                    raise ValueError("采样周期必须大于0")

                diastolic_pressure = self.generate_random_value(80, 10)  # 默认均值和方差
                systolic_pressure = self.generate_random_value(120, 15)  # 默认均值和方差

                self.diastolic_pressures.append(diastolic_pressure)
                self.systolic_pressures.append(systolic_pressure)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                self.timestamps.append(timestamp)

                status = self.determine_blood_pressure_status(systolic_pressure, diastolic_pressure)
                self.statuses.append(status)  # 将状态添加到列表中

                log_message = (f"时间: {timestamp} - "
                               f"舒张压: {diastolic_pressure:.2f}, 收缩压: {systolic_pressure:.2f}, "
                               f"状态: {status}\n")
                self.log_queue.put(log_message)

                time.sleep(sampling_period)
            except ValueError as e:
                error_message = f"输入错误: {e}\n"
                self.log_queue.put(error_message)
                break

    def process_queue(self):
        try:
            while True:
                log_message = self.log_queue.get_nowait()
                self.update_log(log_message)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def update_log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.diastolic_pressures.clear()
        self.systolic_pressures.clear()
        self.timestamps.clear()
        self.statuses.clear()  # 清空状态列表

    def save_to_csv(self):
        # 对数据进行保留一位小数的处理
        rounded_diastolic_pressures = [round(dp, 1) for dp in self.diastolic_pressures]
        rounded_systolic_pressures = [round(sp, 1) for sp in self.systolic_pressures]

        data = {
            '时间': self.timestamps,
            '舒张压': rounded_diastolic_pressures,
            '收缩压': rounded_systolic_pressures,
            '状态': self.statuses  # 添加状态列
        }
        df = pd.DataFrame(data)

        if self.diastolic_pressures:
            diastolic_mean = sum(rounded_diastolic_pressures) / len(rounded_diastolic_pressures)
            diastolic_variance = sum((x - diastolic_mean) ** 2 for x in rounded_diastolic_pressures) / len(rounded_diastolic_pressures)
            df['舒张压均值'] = round(diastolic_mean, 1)
            df['舒张压方差'] = round(diastolic_variance, 1)

        if self.systolic_pressures:
            systolic_mean = sum(rounded_systolic_pressures) / len(rounded_systolic_pressures)
            systolic_variance = sum((x - systolic_mean) ** 2 for x in rounded_systolic_pressures) / len(rounded_systolic_pressures)
            df['收缩压均值'] = round(systolic_mean, 1)
            df['收缩压方差'] = round(systolic_variance, 1)

        df.to_csv("blood_pressure_data.csv", index=False, encoding='utf-8-sig')
        print("数据已保存到 blood_pressure_data.csv")

if __name__ == "__main__":
    root = tk.Tk()
    app = BloodPressureMonitor(root)
    root.mainloop()