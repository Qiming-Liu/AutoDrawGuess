# 旧版本软件

from tkinter import Tk, Canvas, Button, PhotoImage, filedialog
import keyboard
import pyautogui
from PIL import Image, ImageGrab, ImageTk
import win32api, win32gui
import pickle
import numpy as np
from tqdm import tqdm

###################################
# 颜色处理
###################################
diff_limit = 200  # 相似像素最大距离


def colors_diff(pixel_a, pixel_b):
    return np.square(pixel_a[0] - pixel_b[0]) + np.square(pixel_a[1] - pixel_b[1]) + np.square(pixel_a[2] - pixel_b[2])

###################################
# 图像处理
###################################
point_size = 6  # 画笔大小
draw_area = 0.7  # 绘画区域比例
ting = None


###################################
# 屏幕截图
###################################
def get_image():
    hwnd = win32gui.FindWindow(0, 'Draw&Guess')
    if hwnd == 0:
        return None
    else:
        (x1, y1, x2, y2) = win32gui.GetWindowRect(hwnd)
        img = ImageGrab.grab((x1, y1, x2, y2))
        return img


###################################
# 键盘监听
###################################
running = False
target_img_path = ''


def start():
    global running
    if running:
        return 0
    running = True
    # 读取图片 调整图片
    global target_img_path
    if not (target_img_path.endswith('.jpg') or target_img_path.endswith('.png')):
        canvas_print('Please choose image first.')
        running = False
        return 0
    target_img = None
    try:
        target_img = Image.open(target_img_path)
    except:
        canvas_print('Can not open the image.')
        running = False
        return 0

    # screen = get_image()
    filename = 'img2.var'
    f = open(filename, 'rb')
    screen = pickle.load(f)
    f.close()

    if screen is None:
        canvas_print('Can not find Draw&Guess.')
        running = False
        return 0
    width, height = screen.size
    if width != 1920 or height != 1080:
        canvas_print('Only support fullscreen.')
        running = False
        return 0

    # 目标图片过大处理
    tiw, tih = target_img.size
    if tiw * draw_area > tih:
        if tiw > width * draw_area:
            w = width * draw_area
            h = tih * width * draw_area / tiw
            target_img = target_img.resize((round(w), round(h)), Image.ANTIALIAS)
    else:
        if tih > height * draw_area:
            h = height * draw_area
            w = tiw * height * draw_area / tih
            target_img = target_img.resize((round(w), round(h)), Image.ANTIALIAS)
    tiw, tih = target_img.size

    # 绘画区域
    start_x = round((width / 2 * draw_area) - (tiw / 2) + (width * (1 - draw_area) / 2))
    start_y = round((height / 2 * draw_area) - (tih / 2) + (height * (1 - draw_area) / 2))

    # 调整调色板光标

    # 调色板
    color_board = screen.crop((1470, 25, 1770, 125))
    color_board = color_board.load()

    # 统计调色板颜色
    colors = []
    for x in range(300):
        for y in range(100):
            color3 = [color_board[x, y][0], color_board[x, y][1], color_board[x, y][2]]
            colors.append(color3)
    colors = np.array(colors)

    # 建立调色板字典
    color_dic = {}
    for x in range(300):
        for y in range(100):
            color_dic[color_board[x, y]] = (x + 1470, y + 25)

    # 计算最接近的颜色
    def closest(p, colors_all):
        p = np.array(p)
        distances = np.sqrt(np.sum((colors_all - p) ** 2, axis=1))
        index_of_smallest = np.where(distances == np.amin(distances))
        smallest_distance_color = colors[index_of_smallest]
        return smallest_distance_color

    # 目标图片缩小
    tiw, tih = target_img.size
    target_img = target_img.resize((round(tiw / point_size), round(tih / point_size)), Image.ANTIALIAS)
    tiw, tih = target_img.size

    # 为了加快运行速度 减少大量颜色
    target_img = target_img.convert('P', palette=Image.ADAPTIVE, colors=5)
    target_img = target_img.convert('RGB', palette=Image.ADAPTIVE, colors=5)

    global ting
    timg = ImageTk.PhotoImage(target_img)
    canvas.create_image(
        230.0,
        430.0,
        image=timg
    )

    target_img_p = target_img.load()
    color_dic_temp = {}

    def find_color(p, colors_all):
        # 扫描临时字典
        if p in color_dic_temp:
            return color_dic_temp[p]

        # 找最接近的颜色
        color = closest(p, colors_all)
        color = color[0]
        rx, ry = color_dic[(color[0], color[1], color[2])]

        color_dic_temp[p] = (rx, ry)
        return rx, ry

    # 检测是否聚焦

    # 计算所有取色点
    step = {}
    for y in range(tih):
        for x in range(tiw):
            m, n = find_color(target_img_p[x, y], colors)
            if not (m is None):
                # 记录操作步骤
                if not (m, n) in step:
                    step[(m, n)] = []
                step[(m, n)].append((start_x + point_size * x, start_y + point_size * y))

    # 排序, 先画颜色多的点
    sort = sorted(step, key=lambda k: len(step[k]), reverse=True)

    # 最大点间距倍数 默认为2 越大图像越模糊,速度越快
    max_dot_pitch_multiple = 3

    # 选择最小画笔
    # pyautogui.click(1407, 73)

    # 统计需要画的线
    for the_color in tqdm(sort):
        last_point = (0, 0)
        lines = []
        line = {}
        for draw_point in step[the_color]:
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
        pyautogui.PAUSE = 0.05
        pyautogui.click(the_color[0], the_color[1])  # 色板取色

        for the_line in lines:
            pyautogui.PAUSE = 0.02
            pyautogui.click(x=the_line['start'][0], y=the_line['start'][1])
            if 'end' in the_line:
                time = ((((the_line['end'][0] - the_line['start'][0]) ** 2) + (
                        (the_line['end'][1] - the_line['start'][1]) ** 2)) ** 0.5) / point_size / 160
                time = max(0.05, time)
                pyautogui.dragTo(the_line['end'][0], the_line['end'][1], time, button='left')

    running = False


keyboard.add_hotkey('f9', start)

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
        43.0,
        340.0,
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
