from __future__ import division
from tkinter import Tk, Canvas, Button, PhotoImage, filedialog
from PIL import Image, ImageGrab, ImageTk
from win32gui import FindWindow, GetWindowRect
from keyboard import add_hotkey
from pickle import load
import numpy as np
import pyautogui

# 预设值常量
diff_limit = 400  # 相似颜色最大距离
draw_area = 0.72  # 绘画区域比例
pause_point = 0.06  # 画点时间
pause_line = 0.1  # 画线时间
check_game = False  # 是否检测游戏运行
# 屏幕大小 目前只支持全屏1080p
screen_w = 1920
screen_h = 1080

# 运行中变量
img_show = None  # 预览图
running = False  # 是否正在画图
target_img_path = ''  # 用户传入的图片路径
# 获取调色板变量
f = open('./bin/colors_all.bin', 'rb')
colors_all = load(f)
f.close()
f = open('./bin/colors_all_dic.bin', 'rb')
colors_all_dic = load(f)
f.close()


# 计算最接近的颜色
def closest(p):
    p = np.array(p)
    distances = np.sqrt(np.sum((colors_all - p) ** 2, axis=1))
    index_of_smallest = np.where(distances == np.amin(distances))
    smallest_distance_color = colors_all[index_of_smallest]
    return smallest_distance_color[0]


# 颜色距离
def colors_diff(pixel_a, pixel_b):
    return np.square(pixel_a[0] - pixel_b[0]) + np.square(pixel_a[1] - pixel_b[1]) + np.square(pixel_a[2] - pixel_b[2])


# 获取屏幕截图
def get_image():
    hwnd = FindWindow(0, 'Draw&Guess')
    if hwnd == 0:
        return None
    else:
        (x1, y1, x2, y2) = GetWindowRect(hwnd)
        img = ImageGrab.grab((x1, y1, x2, y2))
        return img


def start():
    # 粗糙画图
    point_size = 32  # 画笔大小
    reduce_color = True  # 减少颜色
    color_num = 5  # 颜色数量
    max_dot_pitch_multiple = 0  # 最大连线间距倍数

    global running
    global target_img_path
    global colors_all
    global colors_all_dic

    # 防止多次画图
    if running:
        return 0
    running = True

    # 读取图片
    if not (target_img_path.endswith('.jpg') or target_img_path.endswith('.png')):
        canvas_print('Please choose image first.')
        running = False
        return 0
    try:
        target_img = Image.open(target_img_path)
    except:
        canvas_print('Can not open the image.')
        running = False
        return 0

    # 屏幕截图
    if check_game:
        screen = get_image()
        if screen is None:
            canvas_print('Can not find Draw&Guess.')
            running = False
            return 0
        if screen.size[0] != screen_w or screen.size[1] != screen_h:
            canvas_print('Only support fullscreen 1080p.')
            running = False
            return 0

    # 图片过大
    tw, th = target_img.size
    if tw > th:
        resize = screen_w * draw_area / tw
    else:
        resize = screen_h * draw_area / th
    target_img = target_img.resize((int(tw * resize), int(th * resize)), Image.ANTIALIAS)
    target_img2 = target_img
    tw, th = target_img.size

    # 绘画起始点
    start_x = int((screen_w * 0.5 * draw_area) - (tw * 0.5) + (screen_w * (1 - draw_area) * 0.5) + point_size * 0.5)
    start_y = int((screen_h * 0.5 * draw_area) - (th * 0.5) + (screen_h * (1 - draw_area) * 0.5) + point_size * 0.5)

    # 目标图片缩小
    tw, th = target_img.size
    target_img = target_img.resize((round(tw / point_size), round(th / point_size)), Image.ANTIALIAS)
    tw, th = target_img.size

    # 减少大量颜色
    if reduce_color:
        target_img = target_img.convert('P', palette=Image.ADAPTIVE, colors=color_num)
        target_img = target_img.convert('RGB', palette=Image.ADAPTIVE, colors=color_num)
    target_img_p = target_img.load()

    color_dic_temp = {}  # 临时字典
    def find_color(p):
        # 忽略白色
        if colors_diff((255, 254, 246), p) < diff_limit:
            return None, None

        # 扫描临时字典
        if p in color_dic_temp:
            return color_dic_temp[p]

        # 找最接近的颜色
        color = closest(p)

        # 获取坐标
        rx, ry = colors_all_dic[(color[0], color[1], color[2])]

        color_dic_temp[p] = (rx, ry)
        return rx, ry

    # 计算所有取色点
    draw_step = {}
    for y in range(th):  # 先横着画
        for x in range(tw):
            m, n = find_color(target_img_p[x, y])
            if not (m is None):
                # 记录操作步骤
                if not (m, n) in draw_step:
                    draw_step[(m, n)] = []
                draw_step[(m, n)].append((start_x + point_size * x, start_y + point_size * y))

    # 排序, 先画颜色多的点
    sort = sorted(draw_step, key=lambda k: len(draw_step[k]), reverse=True)

    # 选择最大画笔
    if check_game:
        pyautogui.click(1307, 73)

    # 删除最浅的颜色
    if len(sort) == color_num:
        sort.remove(color_dic_temp[max(list(color_dic_temp.keys()))])

    # 统计需要画的线
    for the_color in sort:
        last_point = (0, 0)
        lines = []
        line = {}
        for draw_point in draw_step[the_color]:
            # 同一行 且 距离够近
            if draw_point[1] == last_point[1] and not abs(
                    draw_point[0] - last_point[0]) > max_dot_pitch_multiple * point_size:
                line['end'] = draw_point
            else:
                if last_point[0] != 0:
                    lines.append(line)
                    line = {}
                line['start'] = draw_point
            last_point = draw_point

        # 画线
        pyautogui.PAUSE = pause_point
        pyautogui.click(the_color[0], the_color[1])  # 色板取色
        for the_line in lines:
            pyautogui.click(x=the_line['start'][0], y=the_line['start'][1])
            if 'end' in the_line:
                time = ((((the_line['end'][0] - the_line['start'][0]) ** 2) + (
                            (the_line['end'][1] - the_line['start'][1]) ** 2)) ** 0.5) / point_size * 0.025
                time = max(pause_line, time)
                pyautogui.dragTo(the_line['end'][0], the_line['end'][1], time, button='left')

    draw2(target_img2)

    running = False

    window.exit()

# 精细画图
def draw2(target_img2):
    point_size = 10  # 画笔大小
    reduce_color = True  # 减少颜色
    color_num = 5  # 颜色数量
    max_dot_pitch_multiple = 4  # 最大连线间距倍数

    global img_show
    global target_img_path
    global colors_all
    global colors_all_dic

    target_img = target_img2
    tw, th = target_img.size

    # 绘画起始点
    start_x = int((screen_w * 0.5 * draw_area) - (tw * 0.5) + (screen_w * (1 - draw_area) * 0.5) + point_size * 0.5)
    start_y = int((screen_h * 0.5 * draw_area) - (th * 0.5) + (screen_h * (1 - draw_area) * 0.5) + point_size * 0.5)

    # 目标图片缩小
    tw, th = target_img.size
    target_img = target_img.resize((round(tw / point_size), round(th / point_size)), Image.ANTIALIAS)
    tw, th = target_img.size

    # 减少大量颜色
    if reduce_color:
        target_img = target_img.convert('P', palette=Image.ADAPTIVE, colors=color_num)
        target_img = target_img.convert('RGB', palette=Image.ADAPTIVE, colors=color_num)
    target_img_p = target_img.load()

    # 显示预览图
    img_show = ImageTk.PhotoImage(target_img)
    canvas.create_image(
        230.0,
        430.0,
        image=img_show
    )

    color_dic_temp = {}  # 临时字典
    def find_color(p):
        # 忽略白色
        if colors_diff((255, 254, 246), p) < diff_limit:
            return None, None

        # 扫描临时字典
        if p in color_dic_temp:
            return color_dic_temp[p]

        # 找最接近的颜色
        color = closest(p)

        # 获取坐标
        rx, ry = colors_all_dic[(color[0], color[1], color[2])]

        color_dic_temp[p] = (rx, ry)
        return rx, ry

    # 计算所有取色点
    draw_step = {}
    for y in range(th):  # 先横着画
        for x in range(tw):
            m, n = find_color(target_img_p[x, y])
            if not (m is None):
                # 记录操作步骤
                if not (m, n) in draw_step:
                    draw_step[(m, n)] = []
                draw_step[(m, n)].append((start_x + point_size * x, start_y + point_size * y))

    # 排序, 先画颜色多的点
    sort = sorted(draw_step, key=lambda k: len(draw_step[k]), reverse=True)

    # 选择中等画笔
    if check_game:
        pyautogui.click(1357, 73)

    # 删除最浅的颜色
    if len(sort) == color_num:
        sort.remove(color_dic_temp[max(list(color_dic_temp.keys()))])

    # 统计需要画的线
    for the_color in sort:
        last_point = (0, 0)
        lines = []
        line = {}
        for draw_point in draw_step[the_color]:
            # 同一行 且 距离够近
            if draw_point[1] == last_point[1] and not abs(
                    draw_point[0] - last_point[0]) > max_dot_pitch_multiple * point_size:
                line['end'] = draw_point
            else:
                if last_point[0] != 0:
                    lines.append(line)
                    line = {}
                line['start'] = draw_point
            last_point = draw_point

        # 画线
        pyautogui.PAUSE = pause_point
        pyautogui.click(the_color[0], the_color[1])  # 色板取色
        for the_line in lines:
            pyautogui.click(x=the_line['start'][0], y=the_line['start'][1])
            if 'end' in the_line:
                time = ((((the_line['end'][0] - the_line['start'][0]) ** 2) + (
                        (the_line['end'][1] - the_line['start'][1]) ** 2)) ** 0.5) / point_size * 0.025
                time = max(pause_line, time)
                pyautogui.dragTo(the_line['end'][0], the_line['end'][1], time, button='left')

add_hotkey('f9', start)

###################################
# 主程序
###################################

# 创建程序
window = Tk()
window.geometry("650x537")
window.configure(bg="#FFFFFF")
window.iconbitmap(r'.\app.ico')
window.title('Autodraw')

# 背景图
canvas = Canvas(
    window,
    bg="#FFFFFF",
    height=537,
    width=650,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)
canvas.place(x=0, y=0)
image_image = PhotoImage(
    file="./assets/bg.png")
canvas.create_image(
    325.0,
    268.0,
    image=image_image
)


def create_text(t):
    canvas.create_text(
        20.0,
        20.0,
        anchor="nw",
        text=t,
        tags=('print',)
    )


def canvas_print(t):
    canvas.delete('print')
    create_text(t)


def button_clicked():
    global target_img_path
    target_img_path = filedialog.askopenfilename(title="Select An Image",
                                                 filetypes=(("jpeg files", "*.jpg"), ("png files", "*.png")))
    canvas_print(target_img_path)


# 加载图片按钮
button_image = PhotoImage(
    file="./assets/button.png")
button = Button(
    image=button_image,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: button_clicked(),
    relief="flat"
)
button.place(
    x=451.0,
    y=124.0,
    width=198.0,
    height=143.0
)
create_text("Waiting for the image.")
window.resizable(False, False)
window.mainloop()
