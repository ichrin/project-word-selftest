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
        self.root.geometry("740x620")
        
        # 数据
        self.all_words = []
        self.words = []
        self.qs = []
        self.idx = 0
        self.score = 0
        self.total = 0
        self.wrong = []
        self.wrong_words = []
        self.mastered_words = []
        self.mode = 0
        self.cur_word = None
        self.csv_files = []
        self.cur_file = None
        self.quiz_num = 20
        self.sel_var = tk.IntVar(value=-1)
        self.wrong_file = None
        self.is_wrong_mode = False
        self.skip_mastered = tk.BooleanVar(value=False)
        self.need_record = False
        
        # 词性筛选选项
        self.pos_filters = {
            "名": tk.BooleanVar(value=True),
            "动": tk.BooleanVar(value=True),
            "形": tk.BooleanVar(value=True),
            "副": tk.BooleanVar(value=True),
            "連体": tk.BooleanVar(value=True),
            "接": tk.BooleanVar(value=True),
            "感": tk.BooleanVar(value=True),
            "接頭": tk.BooleanVar(value=True),
            "接尾": tk.BooleanVar(value=True),
            "助": tk.BooleanVar(value=True),
            "固名": tk.BooleanVar(value=True),
            "其他": tk.BooleanVar(value=True),
        }
        
        # 词性映射
        self.pos_mapping = {
            "名": "名", "名词": "名",
            "动": "动", "动词": "动",
            "他": "动", "自": "动",
            "他动": "动", "自动": "动",
            "他Ⅰ": "动", "他II": "动", "他Ⅱ": "动",
            "他III": "动", "他Ⅲ": "动",
            "自Ⅰ": "动", "自II": "动", "自Ⅱ": "动",
            "自III": "动", "自Ⅲ": "动",
            "他I": "动", "自I": "动",
            "形": "形", "形容词": "形",
            "形I": "形", "形II": "形",
            "形Ⅰ": "形", "形Ⅱ": "形",
            "イ形": "形", "ナ形": "形",
            "副": "副", "副词": "副",
            "連体": "連体", "连体": "連体",
            "接": "接", "接続": "接", "接续": "接",
            "感": "感", "感叹": "感",
            "接頭": "接頭", "接头": "接頭",
            "接尾": "接尾",
            "助": "助", "助词": "助",
            "格助": "助", "接助": "助",
            "終助": "助", "並助": "助",
            "取立助": "助", "取立て助": "助",
            "準助": "助", "準体": "助",
            "固名": "固名", "固有名": "固名", "专名": "固名",
        }
        
        self.setup_ui()
        self.load_mastered()
        self.load_all_csv()
    
    def normalize_pos(self, pos):
        if not pos:
            return "其他"
        pos = pos.strip()
        pos = re.sub(r'[＜<].*[＞>]', '', pos)
        pos = pos.replace('＜', '').replace('＞', '').replace('<', '').replace('>', '')
        pos = pos.strip()
        
        separators = ['・', '/', '、', '，', ',']
        parts = [pos]
        for sep in separators:
            if sep in pos:
                parts = pos.split(sep)
                break
        
        for part in parts:
            part = part.strip()
            if part in self.pos_mapping:
                return self.pos_mapping[part]
            if '动' in part or '他' in part or '自' in part:
                return "动"
            if '形' in part or '容' in part:
                return "形"
            if '名' in part:
                return "名"
            if '副' in part:
                return "副"
            if '助' in part:
                return "助"
            if '接' in part and '頭' not in part and '尾' not in part:
                return "接"
        return "其他"
    
    def is_kana_word(self, text):
        clean = re.sub(r'[（(）).]', '', text)
        kana_pattern = re.compile(r'^[\u30A0-\u30FF\u30FC]+$')
        return bool(kana_pattern.match(clean))
    
    def is_katakana_word(self, text):
        """判断是否为纯片假名单词（外来语）"""
        clean = re.sub(r'[（(）).]', '', text)
        katakana_pattern = re.compile(r'^[\u30A0-\u30FF\u30FC]+$')
        return bool(katakana_pattern.match(clean))
    
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
        clean = re.sub(r'[⓪①②③④⑤⑥⑦⑧⑨⑩]', '', reading)
        clean = re.sub(r'[（(）).]', '', clean)
        return clean.strip()
    
    def get_word_key(self, word):
        return f"{word['jp']}|{word['cn']}"
    
    def is_mastered(self, word):
        key = self.get_word_key(word)
        return key in self.mastered_words
    
    def load_mastered(self):
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
        try:
            with open("mastered.txt", "w", encoding="utf-8") as fp:
                for key in self.mastered_words:
                    fp.write(key + "\n")
        except:
            pass
    
    def add_mastered(self, word):
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
        
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_frame = tk.Frame(main_frame, width=340)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        left_frame.pack_propagate(False)
        
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # --- 左侧控制区 ---
        tk.Label(left_frame, text="测验模式:", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        # 第一行模式
        mode_frame1 = tk.Frame(left_frame)
        mode_frame1.pack(anchor=tk.W, fill=tk.X)
        self.mode_var = tk.StringVar(value="jp2cn")
        modes1 = [("日译中", "jp2cn"), ("中译日", "cn2jp"), ("词性", "full")]
        for t, v in modes1:
            tk.Radiobutton(mode_frame1, text=t, variable=self.mode_var, 
                          value=v, command=self.set_mode).pack(side=tk.LEFT, padx=2)
        
        # 第二行模式
        mode_frame2 = tk.Frame(left_frame)
        mode_frame2.pack(anchor=tk.W, fill=tk.X)
        modes2 = [("读音", "reading"), ("假名->汉字", "kana2kanji")]
        for t, v in modes2:
            tk.Radiobutton(mode_frame2, text=t, variable=self.mode_var, 
                          value=v, command=self.set_mode).pack(side=tk.LEFT, padx=2)
        
        # 第三行：外来语模式
        mode_frame3 = tk.Frame(left_frame)
        mode_frame3.pack(anchor=tk.W, fill=tk.X)
        tk.Label(mode_frame3, text="【外来语】", fg="purple", font=("微软雅黑", 9, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(mode_frame3, text="日译中", variable=self.mode_var, 
                      value="kata_jp2cn", command=self.set_mode).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(mode_frame3, text="中译日", variable=self.mode_var, 
                      value="kata_cn2jp", command=self.set_mode).pack(side=tk.LEFT, padx=2)
        
        tk.Frame(left_frame, height=10).pack()
        
        # 词性筛选区域
        self.pos_frame = tk.LabelFrame(left_frame, text="词性筛选 (仅词性模式)", font=("微软雅黑", 9))
        self.pos_frame.pack(fill=tk.X, pady=5)
        
        pos_categories = [
            ("动词", ["动"]),
            ("形容词", ["形"]),
            ("名词", ["名"]),
            ("助词", ["助"]),
            ("其他", ["副", "連体", "接", "感", "接頭", "接尾", "固名", "其他"]),
        ]
        
        for cat_name, pos_list in pos_categories:
            cat_frame = tk.Frame(self.pos_frame)
            cat_frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(cat_frame, text=cat_name+":", font=("微软雅黑", 8), width=6).pack(side=tk.LEFT)
            for p in pos_list:
                if p in self.pos_filters:
                    cb = tk.Checkbutton(cat_frame, text=p, variable=self.pos_filters[p],
                                       command=self.on_pos_filter_changed, font=("微软雅黑", 8))
                    cb.pack(side=tk.LEFT, padx=2)
        
        pos_btn_frame = tk.Frame(self.pos_frame)
        pos_btn_frame.pack(fill=tk.X, pady=3)
        tk.Button(pos_btn_frame, text="全选动词", command=self.select_verbs_only, 
                 font=("微软雅黑", 8), width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(pos_btn_frame, text="全选", command=self.select_all_pos, 
                 font=("微软雅黑", 8), width=6).pack(side=tk.LEFT, padx=2)
        tk.Button(pos_btn_frame, text="取消全选", command=self.deselect_all_pos, 
                 font=("微软雅黑", 8), width=8).pack(side=tk.LEFT, padx=2)
        
        self.pos_count_lb = tk.Label(self.pos_frame, text="当前筛选: 0 个单词", fg="blue", font=("微软雅黑", 8))
        self.pos_count_lb.pack(pady=2)
        
        self.pos_stat_lb = tk.Label(self.pos_frame, text="", fg="gray", font=("微软雅黑", 7), wraplength=320)
        self.pos_stat_lb.pack(pady=2)
        
        tk.Frame(left_frame, height=10).pack()
        
        self.wrong_btn = tk.Button(left_frame, text="错题训练 (0)", command=self.start_wrong_mode,
                                   fg="red", width=15)
        self.wrong_btn.pack(anchor=tk.W, pady=2)
        
        tk.Checkbutton(left_frame, text="排除已掌握单词", 
                      variable=self.skip_mastered,
                      command=self.on_skip_changed).pack(anchor=tk.W, pady=2)
        
        num_frame = tk.Frame(left_frame)
        num_frame.pack(anchor=tk.W, pady=5)
        tk.Label(num_frame, text="每题数:").pack(side=tk.LEFT)
        self.num_var = tk.StringVar(value="20")
        num_spin = tk.Spinbox(num_frame, from_=5, to=50, width=4, 
                              textvariable=self.num_var, command=self.set_quiz_num)
        num_spin.pack(side=tk.LEFT, padx=5)
        
        tk.Frame(left_frame, height=10).pack()
        
        self.mastered_lb = tk.Label(left_frame, text="已掌握: 0 个", fg="green", anchor=tk.W)
        self.mastered_lb.pack(fill=tk.X, pady=2)
        
        self.file_lb = tk.Label(left_frame, text="CSV: 0  |  词数: 0", fg="blue", anchor=tk.W, wraplength=320)
        self.file_lb.pack(fill=tk.X, pady=2)
        
        self.mode_hint = tk.Label(left_frame, text="", fg="red", anchor=tk.W)
        self.mode_hint.pack(fill=tk.X, pady=2)
        
        # --- 右侧题目区 ---
        self.info_lb = tk.Label(right_frame, text="单词: 0  |  得分: 0/0", font=("微软雅黑", 10))
        self.info_lb.pack(pady=5)
        
        self.q_lb = tk.Label(right_frame, text="", font=("微软雅黑", 14), wraplength=400, justify=tk.CENTER)
        self.q_lb.pack(pady=20)
        
        self.opt_btns = []
        of = tk.Frame(right_frame)
        of.pack(pady=10)
        
        for i in range(4):
            rb = tk.Radiobutton(of, text="", variable=self.sel_var, value=i, font=("微软雅黑", 11))
            rb.pack(anchor=tk.W, pady=3)
            self.opt_btns.append(rb)
        
        bf = tk.Frame(right_frame)
        bf.pack(pady=15)
        
        self.submit_btn = tk.Button(bf, text="提交", command=self.submit, width=8)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = tk.Button(bf, text="下一题", command=self.next_q, 
                                  state=tk.DISABLED, width=8)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        self.restart_btn = tk.Button(bf, text="重新开始", command=self.restart, width=8)
        self.restart_btn.pack(side=tk.LEFT, padx=5)
        
        self.res_lb = tk.Label(right_frame, text="", font=("微软雅黑", 12))
        self.res_lb.pack(pady=10)
    
    def select_verbs_only(self):
        for var in self.pos_filters.values():
            var.set(False)
        self.pos_filters["动"].set(True)
        self.on_pos_filter_changed()
    
    def select_all_pos(self):
        for var in self.pos_filters.values():
            var.set(True)
        self.on_pos_filter_changed()
    
    def deselect_all_pos(self):
        for var in self.pos_filters.values():
            var.set(False)
        self.on_pos_filter_changed()
    
    def on_pos_filter_changed(self):
        if self.mode == 2:
            pool = self.get_word_pool()
            self.pos_count_lb.config(text=f"当前筛选: {len(pool)} 个单词")
            self.update_pos_stats()
            self.restart()
    
    def update_pos_stats(self):
        if not self.all_words:
            return
        stats = {}
        for w in self.all_words:
            norm = self.normalize_pos(w['pos'])
            stats[norm] = stats.get(norm, 0) + 1
        items = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:6]
        text = "词性分布: " + "  ".join([f"{k}={v}" for k, v in items])
        self.pos_stat_lb.config(text=text)
    
    def on_skip_changed(self):
        self.restart()
    
    def set_quiz_num(self):
        try:
            v = int(self.num_var.get())
            if v >= 5 and v <= 50:
                self.quiz_num = v
        except:
            pass
    
    def set_mode(self):
        mode_map = {
            "jp2cn": 0, "cn2jp": 1, "full": 2, 
            "reading": 3, "kana2kanji": 4,
            "kata_jp2cn": 5, "kata_cn2jp": 6
        }
        new_mode = mode_map.get(self.mode_var.get(), 0)
        
        # 外来语模式检查
        if new_mode in [5, 6]:
            kata_words = [w for w in self.all_words if self.is_katakana_word(w['jp'])]
            if len(kata_words) < 3:
                messagebox.showwarning("提示", "当前词库中片假名单词（外来语）不足3个")
                return
        
        if new_mode == 3:
            has_reading_words = [w for w in self.all_words if self.has_reading(w)]
            if len(has_reading_words) < 5:
                messagebox.showwarning("提示", "当前词库中可考读音的单词不足5个")
                return
        
        if new_mode == 4:
            kanji_words = [w for w in self.all_words if self.is_kanji_word(w['jp']) and self.has_reading(w)]
            if len(kanji_words) < 5:
                messagebox.showwarning("提示", "当前词库中可考汉字的单词不足5个")
                return
        
        self.is_wrong_mode = False
        self.mode_hint.config(text="")
        
        # 外来语模式提示
        if new_mode == 5:
            self.mode_hint.config(text="【外来语 日译中】", fg="purple")
        elif new_mode == 6:
            self.mode_hint.config(text="【外来语 中译日】", fg="purple")
        
        self.mode = new_mode
        
        if new_mode == 2:
            self.update_pos_stats()
            pool = self.get_word_pool()
            self.pos_count_lb.config(text=f"当前筛选: {len(pool)} 个单词")
        else:
            self.pos_count_lb.config(text="")
            if new_mode not in [5, 6]:
                self.pos_stat_lb.config(text="")
        
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
            self.file_lb.config(text="未找到CSV文件", fg="red")
            self.q_lb.config(text="请将CSV文件放在程序所在文件夹")
            return
        
        total = 0
        for f in files:
            cnt = self.load_csv_file(f)
            total += cnt
        
        self.file_lb.config(text=f"CSV: {len(files)}  |  词数: {total}", fg="blue")
        self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个", fg="green")
        
        if self.all_words:
            # 统计外来语数量
            kata_cnt = len([w for w in self.all_words if self.is_katakana_word(w['jp'])])
            self.file_lb.config(text=f"CSV: {len(files)}  |  词数: {total}  |  外来语: {kata_cnt}", fg="blue")
            self.update_pos_stats()
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
        base = self.all_words if not self.is_wrong_mode else self.wrong_words
        
        if self.mode == 3:
            pool = [w for w in base if self.has_reading(w)]
        elif self.mode == 4:
            pool = [w for w in base if self.is_kanji_word(w['jp']) and self.has_reading(w)]
        elif self.mode == 5:
            pool = [w for w in base if self.is_katakana_word(w['jp'])]
        elif self.mode == 6:
            pool = [w for w in base if self.is_katakana_word(w['jp'])]
        elif self.mode == 2:
            selected_pos = [p for p, var in self.pos_filters.items() if var.get()]
            if selected_pos:
                pool = []
                for w in base:
                    norm_pos = self.normalize_pos(w['pos'])
                    if norm_pos in selected_pos:
                        pool.append(w)
            else:
                pool = []
        else:
            pool = base[:]
        
        if self.skip_mastered.get():
            pool = [w for w in pool if not self.is_mastered(w)]
        
        return pool
    
    def restart(self):
        pool = self.get_word_pool()
        
        if self.mode == 2:
            self.pos_count_lb.config(text=f"当前筛选: {len(pool)} 个单词")
        
        if not pool:
            msg = "当前没有可用的单词"
            if self.skip_mastered.get():
                msg += "（已掌握单词已被排除）"
                if messagebox.askyesno("提示", msg + "。是否取消排除已掌握单词？"):
                    self.skip_mastered.set(False)
                    self.restart()
                return
            elif self.mode == 2:
                selected = [p for p, var in self.pos_filters.items() if var.get()]
                if selected:
                    msg += "（当前词性筛选条件过严）"
                    if messagebox.askyesno("提示", msg + "。是否选择所有词性？"):
                        self.select_all_pos()
                        self.restart()
                    return
                else:
                    msg += "（请至少选择一个词性）"
                    messagebox.showwarning("提示", msg)
                    return
            elif self.mode in [5, 6]:
                msg += "（请检查CSV中是否有片假名单词）"
                messagebox.showwarning("提示", msg)
                return
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
        self.submit_btn.config(text="提交", command=self.submit, state=tk.NORMAL)
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
        self.submit_btn.config(text="提交", command=self.submit, state=tk.NORMAL)
        self.next_btn.config(state=tk.DISABLED)
        
        mode_text = "错题训练" if self.is_wrong_mode else "普通"
        mode_names = ["日译中", "中译日", "词性", "读音", "假名->汉字", "外来语日译中", "外来语中译日"]
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
        elif mode == 4:
            reading_display = self.get_reading_for_display(w['reading'])
            return f"第{self.idx+1}题（共{self.total}题） 选择对应的日语（汉字）：\n\n【{reading_display}】"
        elif mode == 5:
            return f"第{self.idx+1}题（共{self.total}题） 【外来语】选择正确的中文释义：\n\n{w['jp']}"
        else:  # mode == 6
            return f"第{self.idx+1}题（共{self.total}题） 【外来语】选择正确的片假名：\n\n{w['cn']}"
    
    def get_opts(self, w):
        mode = self.mode
        base_pool = self.all_words if not self.is_wrong_mode else self.wrong_words
        random.shuffle(base_pool)
        
        if mode == 0:
            correct = w['cn']
            wrong = []
            for p in base_pool:
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
            for p in base_pool:
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
            for p in base_pool:
                if p['pos'] != correct and p['pos'] not in wrong and p['pos']:
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
            reading_pool = [p for p in base_pool if p['reading'] and p['reading'].strip() != '']
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
        elif mode == 4:
            correct = w['jp']
            kanji_pool = [p for p in base_pool if self.is_kanji_word(p['jp']) and self.has_reading(p)]
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
        elif mode == 5:
            # 外来语 日译中
            correct = w['cn']
            kata_pool = [p for p in base_pool if self.is_katakana_word(p['jp'])]
            wrong = []
            for p in kata_pool:
                if p['cn'] != correct and p['cn'] not in wrong:
                    wrong.append(p['cn'])
                if len(wrong) >= 3:
                    break
            while len(wrong) < 3:
                wrong.append("---")
            opts = [correct] + wrong[:3]
            random.shuffle(opts)
            return opts
        else:  # mode == 6 外来语 中译日
            correct = w['jp']
            kata_pool = [p for p in base_pool if self.is_katakana_word(p['jp'])]
            wrong = []
            for p in kata_pool:
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
        elif mode == 4:
            correct = w['jp']
        elif mode == 5:
            correct = w['cn']
        else:  # mode == 6
            correct = w['jp']
        
        chosen = opts[sel]
        is_correct = (chosen == correct)
        
        if is_correct:
            self.score += 1
            self.res_lb.config(text="回答正确！", fg="green")
            self.add_mastered(w)
            self.need_record = True
            self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个", fg="green")
        else:
            wrong_entry = f"{w['jp']}|{w['reading']}|{w['pos']}|{w['cn']}|{w.get('src','')}"
            self.wrong.append(wrong_entry)
            self.res_lb.config(text=f"回答错误。正确答案：{correct}", fg="red")
            self.submit_btn.config(text="订正", command=self.correct_submit)
        
        self.submit_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL)
        mode_names = ["日译中", "中译日", "词性", "读音", "假名->汉字", "外来语日译中", "外来语中译日"]
        mode_text = "错题训练" if self.is_wrong_mode else "普通"
        skip_text = " [排除已掌握]" if self.skip_mastered.get() else ""
        self.info_lb.config(text=f"[{mode_text}/{mode_names[self.mode]}{skip_text}] 单词: {len(self.words)}  |  得分: {self.score}/{self.total}")
    
    def correct_submit(self):
        self.submit_btn.config(text="确认订正", command=self.confirm_correct, state=tk.NORMAL)
        self.res_lb.config(text="请重新选择正确答案进行订正", fg="blue")
    
    def confirm_correct(self):
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
        elif mode == 4:
            correct = w['jp']
        elif mode == 5:
            correct = w['cn']
        else:
            correct = w['jp']
        
        chosen = opts[sel]
        
        if chosen == correct:
            self.add_mastered(w)
            self.mastered_lb.config(text=f"已掌握: {len(self.mastered_words)} 个", fg="green")
            self.res_lb.config(text="订正正确！已记录为掌握", fg="green")
            
            wrong_key = f"{w['jp']}|{w['reading']}|{w['pos']}|{w['cn']}"
            self.wrong = [item for item in self.wrong if wrong_key not in item]
        else:
            self.res_lb.config(text=f"订正错误。正确答案：{correct}。请继续订正", fg="red")
            self.submit_btn.config(text="确认订正", command=self.confirm_correct, state=tk.NORMAL)
            return
        
        self.submit_btn.config(text="提交", command=self.submit, state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL)
    
    def next_q(self):
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