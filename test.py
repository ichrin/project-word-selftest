# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import random
import os
import glob
import re
from datetime import datetime

class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("单词小测")
        self.root.geometry("700x580")
        
        # 数据
        self.all_words = []
        self.words = []
        self.qs = []
        self.idx = 0
        self.score = 0
        self.total = 0
        self.wrong = []
        self.wrong_words = []
        self.mastered_words = []  # 已掌握单词列表
        self.mode = 0  # 0: 日译中, 1: 中译日, 2: 词性, 3: 读音, 4: 假名->汉字
        self.cur_word = None
        self.csv_files = []
        self.cur_file = None
        self.quiz_num = 20
        self.sel_var = tk.IntVar(value=-1)
        self.wrong_file = None
        self.is_wrong_mode = False
        self.skip_mastered = tk.BooleanVar(value=False)  # 是否跳过已掌握单词
        self.need_record = False  # 当前题是否需要记录（答对或订正后记录）
        
        self.setup_ui()
        self.load_mastered()  # 加载已掌握单词记录
        self.load_all_csv()
    
    def is_kana_word(self, text):
        clean = re.sub(r'[（(）).]', '', text)
        kana_pattern = re.compile(r'^[\u30A0-\u30FF\u30FC]+$')
        return bool(kana_pattern.match(clean))
    
    def has_reading(self, word):
        if self.is_kana_word(word['jp']):
            return False
        if not word['reading'] or word['reading'].strip() == '':
            return False
        return True
    
    def is_kanji_word(self, text):
        kanji_pattern = re.compile(r'[\u4E00-\u9FFF]')
        return bool(kanji_pattern.search(text))
    
    def get_reading_for_display(self, reading):
        clean = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', '', reading)
        clean = re.sub(r'[（(）).]', '', clean)
        return clean.strip()
    
    def get_word_key(self, word):
        """生成单词的唯一标识"""
        return f"{word['jp']}|{word['cn']}"
    
    def is_mastered(self, word):
        """判断单词是否已掌握"""
        key = self.get_word_key(word)
        return key in self.mastered_words
    
    def load_mastered(self):
        """加载已掌握单词记录"""
        self.mastered_words = []
        if os.path.exists("mastered.txt"):
            try:
                with open("mastered.txt", "r", encoding="utf-8") as fp:
                    for line in fp:
                        line = line.strip()
                        if line:
                            self.mastered_words.append(line)
            except:
                pass
    
    def save_mastered(self):
        """保存已掌握单词记录"""
        try:
            with open("mastered.txt", "w", encoding="utf-8") as fp:
                for key in self.mastered_words:
                    fp.write(key + "\n")
        except:
            pass
    
    def add_mastered(self, word):
        """添加单词到已掌握列表"""
        key = self.get_word_key(word)
        if key not in self.mastered_words:
            self.mastered_words.append(key)
            self.save_mastered()
    
    def setup_ui(self):
        mb = tk.Menu(self.root)
        self.root.config(menu=mb)
        
        fm = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="文件", menu=fm)
        fm.add_command(label="重新加载所有CSV", command=self.load_all_csv)
        fm.add_command(label="导入错题", command=self.import_wrong)
        fm.add_separator()
        fm.add_command(label="退出", command=self.root.quit)
        
        # 模式选择 - 第一行
        mf = tk.Frame(self.root)
        mf.pack(pady=5)
        
        tk.Label(mf, text="测验模式:").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="jp2cn")
        
        modes_row1 = [("日译中", "jp2cn"), ("中译日", "cn2jp"), ("词性", "full"), ("读音", "reading")]
        for t, v in modes_row1:
            tk.Radiobutton(mf, text=t, variable=self.mode_var, 
                          value=v, command=self.set_mode).pack(side=tk.LEFT, padx=5)
        
        # 模式选择 - 第二行
        mf2 = tk.Frame(self.root)
        mf2.pack(pady=2)
        
        tk.Radiobutton(mf2, text="假名->汉字", variable=self.mode_var, 
                      value="kana2kanji", command=self.set_mode).pack(side=tk.LEFT, padx=5)
        
        # 错题训练按钮
        self.wrong_btn = tk.Button(mf2, text="错题训练 (0)", command=self.start_wrong_mode,
                                   fg="red", width=10)
        self.wrong_btn.pack(side=tk.LEFT, padx=10)
        
        # 跳过已掌握单词的复选框
        self.skip_cb = tk.Checkbutton(mf2, text="排除已掌握", 
                                      variable=self.skip_mastered,
                                      command=self.on_skip_changed)
        self.skip_cb.pack(side=tk.LEFT, padx=10)
        
        # 每轮题数
        tk.Label(mf2, text="每题数:").pack(side=tk.LEFT, padx=(20,5))
        self.num_var = tk.StringVar(value="20")
        num_spin = tk.Spinbox(mf2, from_=5, to=50, width=4, 
                              textvariable=self.num_var, command=self.set_quiz_num)
        num_spin.pack(side=tk.LEFT)
        
        # 已掌握单词计数
        self.mastered_lb = tk.Label(self.root, text="已掌握: 0 个单词", fg="green")
        self.mastered_lb.pack(pady=2)
        
        # 文件信息
        self.file_lb = tk.Label(self.root, text="CSV文件: 0  |  总词数: 0", fg="blue")
        self.file_lb.pack(pady=2)
        
        # 模式提示
        self.mode_hint = tk.Label(self.root, text="", fg="red", font=("微软雅黑", 10))
        self.mode_hint.pack(pady=2)
        
        # 得分信息
        self.info_lb = tk.Label(self.root, text="单词: 0  |  得分: 0/0")
        self.info_lb.pack(pady=5)
        
        # 题目
        self.q_lb = tk.Label(self.root, text="", font=("微软雅黑", 14), wraplength=640)
        self.q_lb.pack(pady=20)
        
        # 选项
        self.opt_btns = []
        of = tk.Frame(self.root)
        of.pack(pady=10)
        
        for i in range(4):
            rb = tk.Radiobutton(of, text="", variable=self.sel_var, value=i)
            rb.pack(anchor=tk.W, pady=3)
            self.opt_btns.append(rb)
        
        # 按钮
        bf = tk.Frame(self.root)
        bf.pack(pady=15)
        
        self.submit_btn = tk.Button(bf, text="提交", command=self.submit, width=8)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = tk.Button(bf, text="下一题", command=self.next_q, 
                                  state=tk.DISABLED, width=8)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.restart_btn = tk.Button(bf, text="重新开始", command=self.restart, width=8)
        self.restart_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果
        self.res_lb = tk.Label(self.root, text="", font=("微软雅黑", 12))
        self.res_lb.pack(pady=10)
    
    def on_skip_changed(self):
        """排除已掌握单词选项变更时触发"""
        self.restart()
    
    def set_quiz_num(self):
        try:
            v = int(self.num_var.get())
            if v >= 5 and v <= 50:
                self.quiz_num = v
        except:
            pass
    
    def set_mode(self):
        mode_map = {"jp2cn": 0, "cn2jp": 1, "full": 2, "reading": 3, "kana2kanji": 4}
        new_mode = mode_map.get(self.mode_var.get(), 0)
        
        if new_mode == 3:
            has_reading_words = [w for w in self.all_words if self.has_reading(w)]
            if len(has_reading_words) < 5:
                messagebox.showwarning("提示", "当前词库中可考读音的单词（非片假名）不足5个")
                return
        
        if new_mode == 4:
            kanji_words = [w for w in self.all_words if self.is_kanji_word(w['jp']) and self.has_reading(w)]
            if len(kanji_words) < 5:
                messagebox.showwarning("提示", "当前词库中可考汉字的单词（含汉字且有读音）不足5个")
                return
        
        self.is_wrong_mode = False
        self.mode_hint.config(text="")
        self.mode = new_mode
        self.restart()
    
    def start_wrong_mode(self):
        if not self.wrong_words:
            if messagebox.askyesno("提示", "没有错题记录。是否从错题文件导入？"):
                self.import_wrong()
            return
        
        self.is_wrong_mode = True
        self.mode_hint.config(text="【错题训练模式】", fg="red")
        self.restart()
    
    def load_all_csv(self):
        self.all_words = []
        files = glob.glob("*.csv")
        self.csv_files = files
        
        if not files:
            self.file_lb.config(text="未找到CSV文件，请放入同目录", fg="red")
            self.q_lb.config(text="请将CSV文件放在程序所在文件夹")
            return
        
        total = 0
        for f in files:
            cnt = self.load_csv_file(f)
            total += cnt
        
        self.file_lb.config(text=f"CSV文件: {len(files)}  |  总词数: {total}", fg="blue")
        self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个单词", fg="green")
        
        if self.all_words:
            self.restart()
        else:
            self.q_lb.config(text="CSV文件中未找到有效数据")
    
    def load_csv_file(self, path):
        cnt = 0
        try:
            with open(path, "r", encoding="utf-8") as fp:
                rdr = csv.reader(fp)
                for row in rdr:
                    if len(row) >= 6:
                        self.all_words.append({
                            "lesson": row[0],
                            "unit": row[1],
                            "jp": row[2],
                            "reading": row[3],
                            "pos": row[4],
                            "cn": row[5],
                            "src": os.path.basename(path)
                        })
                        cnt += 1
        except Exception as e:
            print(f"加载 {path} 失败: {e}")
        return cnt
    
    def get_word_pool(self):
        """获取当前可用的单词池（根据模式和排除选项）"""
        base = self.all_words if not self.is_wrong_mode else self.wrong_words
        
        # 根据模式筛选
        if self.mode == 3:
            pool = [w for w in base if self.has_reading(w)]
        elif self.mode == 4:
            pool = [w for w in base if self.is_kanji_word(w['jp']) and self.has_reading(w)]
        else:
            pool = base[:]
        
        # 排除已掌握单词
        if self.skip_mastered.get():
            pool = [w for w in pool if not self.is_mastered(w)]
        
        return pool
    
    def restart(self):
        pool = self.get_word_pool()
        if not pool:
            msg = "当前没有可用的单词"
            if self.skip_mastered.get():
                msg += "（已掌握单词已被排除）"
                if messagebox.askyesno("提示", msg + "。是否取消排除已掌握单词？"):
                    self.skip_mastered.set(False)
                    self.restart()
            else:
                messagebox.showwarning("提示", msg)
            return
        
        self.words = pool
        self.gen_qs()
        self.idx = 0
        self.score = 0
        self.wrong = []
        self.wrong_file = None
        self.sel_var.set(-1)
        self.res_lb.config(text="")
        self.submit_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.DISABLED)
        self.show_q()
    
    def gen_qs(self):
        if not self.words:
            return
        pool = self.words[:]
        random.shuffle(pool)
        n = min(self.quiz_num, len(pool))
        self.qs = pool[:n]
        random.shuffle(self.qs)
        self.total = len(self.qs)
    
    def show_q(self):
        if self.idx >= self.total:
            self.finish()
            return
        
        w = self.qs[self.idx]
        self.cur_word = w
        self.need_record = False
        self.sel_var.set(-1)
        self.res_lb.config(text="")
        self.submit_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.DISABLED)
        
        mode_text = "错题训练" if self.is_wrong_mode else "普通"
        mode_names = ["日译中", "中译日", "词性", "读音", "假名->汉字"]
        skip_text = " [排除已掌握]" if self.skip_mastered.get() else ""
        self.info_lb.config(text=f"[{mode_text}/{mode_names[self.mode]}{skip_text}] 单词: {len(self.words)}  |  得分: {self.score}/{self.total}")
        
        opts = self.get_opts(w)
        q = self.get_q_text(w)
        self.q_lb.config(text=q)
        
        for i, rb in enumerate(self.opt_btns):
            if i < len(opts):
                rb.config(text=opts[i], state=tk.NORMAL)
            else:
                rb.config(text="", state=tk.DISABLED)
    
    def get_q_text(self, w):
        mode = self.mode
        if mode == 0:
            return f"第{self.idx+1}题（共{self.total}题） 选择正确的中文释义：\n\n{w['jp']}  【{w['reading']}】"
        elif mode == 1:
            return f"第{self.idx+1}题（共{self.total}题） 选择正确的日语：\n\n{w['cn']}"
        elif mode == 2:
            return f"第{self.idx+1}题（共{self.total}题） 选择正确的词性：\n\n{w['jp']}  【{w['reading']}】\n{w['cn']}"
        elif mode == 3:
            return f"第{self.idx+1}题（共{self.total}题） 选择正确的读音：\n\n{w['jp']}"
        else:
            reading_display = self.get_reading_for_display(w['reading'])
            return f"第{self.idx+1}题（共{self.total}题） 选择对应的日语（汉字）：\n\n【{reading_display}】"
    
    def get_opts(self, w):
        mode = self.mode
        pool = self.words[:]
        random.shuffle(pool)
        
        if mode == 0:
            correct = w['cn']
            wrong = []
            for p in pool:
                if p['cn'] != correct and p['cn'] not in wrong:
                    wrong.append(p['cn'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
        elif mode == 1:
            correct = w['jp']
            wrong = []
            for p in pool:
                if p['jp'] != correct and p['jp'] not in wrong:
                    wrong.append(p['jp'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
        elif mode == 2:
            correct = w['pos']
            wrong = []
            for p in pool:
                if p['pos'] != correct and p['pos'] not in wrong:
                    wrong.append(p['pos'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
        elif mode == 3:
            correct = w['reading']
            reading_pool = [p for p in pool if p['reading'] and p['reading'].strip() != '']
            wrong = []
            for p in reading_pool:
                if p['reading'] != correct and p['reading'] not in wrong:
                    wrong.append(p['reading'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
        else:
            correct = w['jp']
            kanji_pool = [p for p in pool if self.is_kanji_word(p['jp']) and self.has_reading(p)]
            wrong = []
            for p in kanji_pool:
                if p['jp'] != correct and p['jp'] not in wrong:
                    wrong.append(p['jp'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
    
    def submit(self):
        sel = self.sel_var.get()
        
        if sel == -1:
            messagebox.showinfo("提示", "请先选择一个选项")
            return
        
        opts = []
        for rb in self.opt_btns:
            if rb.cget("state") != tk.DISABLED:
                opts.append(rb.cget("text"))
        
        if sel >= len(opts):
            return
        
        w = self.cur_word
        mode = self.mode
        correct = ""
        if mode == 0:
            correct = w['cn']
        elif mode == 1:
            correct = w['jp']
        elif mode == 2:
            correct = w['pos']
        elif mode == 3:
            correct = w['reading']
        else:
            correct = w['jp']
        
        chosen = opts[sel]
        is_correct = (chosen == correct)
        
        if is_correct:
            self.score += 1
            self.res_lb.config(text="回答正确！", fg="green")
            # 答对即记录为已掌握
            self.add_mastered(w)
            self.need_record = True
            self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个单词", fg="green")
        else:
            wrong_entry = f"{w['jp']}|{w['reading']}|{w['pos']}|{w['cn']}|{w.get('src','')}"
            self.wrong.append(wrong_entry)
            self.res_lb.config(text=f"回答错误。正确答案：{correct}", fg="red")
            # 显示订正按钮
            self.submit_btn.config(text="订正", command=self.correct_submit)
        
        self.submit_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL)
        mode_names = ["日译中", "中译日", "词性", "读音", "假名->汉字"]
        mode_text = "错题训练" if self.is_wrong_mode else "普通"
        skip_text = " [排除已掌握]" if self.skip_mastered.get() else ""
        self.info_lb.config(text=f"[{mode_text}/{mode_names[self.mode]}{skip_text}] 单词: {len(self.words)}  |  得分: {self.score}/{self.total}")
    
    def correct_submit(self):
        """订正功能：点击订正后，如果用户选择了正确答案则记录"""
        # 重新启用提交按钮，但改名为"确认订正"
        self.submit_btn.config(text="确认订正", command=self.confirm_correct, state=tk.NORMAL)
        self.res_lb.config(text="请重新选择正确答案进行订正", fg="blue")
    
    def confirm_correct(self):
        """确认订正：用户选择正确答案后记录为已掌握"""
        sel = self.sel_var.get()
        
        if sel == -1:
            messagebox.showinfo("提示", "请先选择一个选项进行订正")
            return
        
        opts = []
        for rb in self.opt_btns:
            if rb.cget("state") != tk.DISABLED:
                opts.append(rb.cget("text"))
        
        if sel >= len(opts):
            return
        
        w = self.cur_word
        mode = self.mode
        correct = ""
        if mode == 0:
            correct = w['cn']
        elif mode == 1:
            correct = w['jp']
        elif mode == 2:
            correct = w['pos']
        elif mode == 3:
            correct = w['reading']
        else:
            correct = w['jp']
        
        chosen = opts[sel]
        
        if chosen == correct:
            # 订正正确，记录为已掌握
            self.add_mastered(w)
            self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个单词", fg="green")
            self.res_lb.config(text="订正正确！已记录为掌握", fg="green")
            
            # 从错题列表中移除（如果存在）
            wrong_key = f"{w['jp']}|{w['reading']}|{w['pos']}|{w['cn']}"
            self.wrong = [item for item in self.wrong if wrong_key not in item]
        else:
            self.res_lb.config(text=f"订正错误。正确答案：{correct}。请继续订正", fg="red")
            # 订正错误，允许继续尝试
            self.submit_btn.config(text="确认订正", command=self.confirm_correct, state=tk.NORMAL)
            return
        
        # 恢复提交按钮
        self.submit_btn.config(text="提交", command=self.submit, state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL)
    
    def next_q(self):
        # 恢复提交按钮
        self.submit_btn.config(text="提交", command=self.submit, state=tk.NORMAL)
        self.idx += 1
        self.show_q()
    
    def finish(self):
        self.q_lb.config(text=f"测验完成！得分：{self.score}/{self.total}")
        self.submit_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.res_lb.config(text="")
        
        if self.wrong:
            self.auto_export_wrong()
            
            for item in self.wrong:
                parts = item.split("|")
                if len(parts) >= 4:
                    new_word = {
                        "jp": parts[0],
                        "reading": parts[1],
                        "pos": parts[2],
                        "cn": parts[3],
                        "src": "错题"
                    }
                    exists = False
                    for w in self.wrong_words:
                        if w['jp'] == new_word['jp'] and w['cn'] == new_word['cn']:
                            exists = True
                            break
                    if not exists:
                        self.wrong_words.append(new_word)
            
            self.wrong_btn.config(text=f"错题训练 ({len(self.wrong_words)})", fg="red")
            
            msg = f"错题数：{len(self.wrong)}。已自动导出到：{self.wrong_file}\n错题总数：{len(self.wrong_words)}"
            messagebox.showinfo("错题已导出", msg)
        else:
            if self.is_wrong_mode:
                messagebox.showinfo("恭喜", "错题全部掌握！继续加油！")
    
    def auto_export_wrong(self):
        if not self.wrong:
            return
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"wrong_{ts}.txt"
        self.wrong_file = fn
        
        try:
            with open(fn, "w", encoding="utf-8") as fp:
                fp.write(f"错题记录 ({len(self.wrong)} 题)\n")
                fp.write("=" * 55 + "\n\n")
                if self.is_wrong_mode:
                    fp.write("来源：错题训练\n\n")
                for i, item in enumerate(self.wrong, 1):
                    parts = item.split("|")
                    if len(parts) >= 4:
                        src = f"  [来源: {parts[4]}]" if len(parts) > 4 else ""
                        fp.write(f"{i}. 日语: {parts[0]}  读音: {parts[1]}  词性: {parts[2]}  中文: {parts[3]}{src}\n")
        except Exception as e:
            print(f"自动导出失败：{e}")
    
    def import_wrong(self):
        f = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if not f:
            return
        
        try:
            with open(f, "r", encoding="utf-8") as fp:
                lines = fp.readlines()
            
            imported = []
            for line in lines:
                if "日语:" in line and "中文:" in line:
                    parts = line.strip().split("  ")
                    jp = rd = pos = cn = ""
                    for p in parts:
                        if "日语:" in p:
                            jp = p.split("日语:")[1].strip()
                        elif "读音:" in p:
                            rd = p.split("读音:")[1].strip()
                        elif "词性:" in p:
                            pos = p.split("词性:")[1].strip()
                        elif "中文:" in p:
                            cn = p.split("中文:")[1].strip()
                    if jp and cn:
                        new_word = {"jp": jp, "reading": rd, "pos": pos, "cn": cn, "src": "导入"}
                        exists = False
                        for w in self.wrong_words:
                            if w['jp'] == new_word['jp'] and w['cn'] == new_word['cn']:
                                exists = True
                                break
                        if not exists:
                            imported.append(new_word)
            
            if imported:
                self.wrong_words.extend(imported)
                self.wrong_btn.config(text=f"错题训练 ({len(self.wrong_words)})", fg="red")
                messagebox.showinfo("导入成功", f"已导入 {len(imported)} 个错题\n错题总数：{len(self.wrong_words)}")
            else:
                messagebox.showinfo("提示", "未找到有效单词数据")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败：{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()