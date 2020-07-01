import shutil
import webbrowser
import tkinter as tk
import tkinter.messagebox
import nsfc_downloader as nsfc

if __name__ == '__main__':
    # 定义窗口
    window = tk.Tk()
    window.title('国自然结题报告下载')
    window.geometry('380x150')
    window.resizable(0, 0)

    # 变量
    state = tk.StringVar()  # 状态
    nsfc_downloader = nsfc.NsfcDownloader('.', '.')  # 初始化下载器
    nsfc_downloader.debug = False

    # 定义窗口的内容
    frm_main = tk.Frame(window, pady=20, padx=10)
    frm_main.pack(side='top')

    # 第一栏
    tk.Label(frm_main, text="请输入申请号：").grid(row=1, column=1)  # 输入提示
    input_ratify = tk.Entry(frm_main)
    input_ratify.focus()
    input_ratify.grid(row=1, column=2)  # 输入框


    def button_download():
        global state, nsfc_downloader

        # 检查申请号信息
        ratify = input_ratify.get()
        if len(ratify) == 0:
            tk.messagebox.showerror(title='错误', message='请输入有效的国自然项目申请号')
            return

        # 创建暂存文件夹
        tmp_path = './tmp'
        nsfc.mkdir_p(tmp_path)

        # 复用下载器
        nsfc_downloader.tmp_path = tmp_path

        # 在GUI里面重新实现一边download方法，因为要实现状态输出
        state.set('开始获取项目信息，项目编号： {}'.format(ratify))
        ratify_info = nsfc_downloader.get_ratify_info(ratify)
        if not ratify_info['success']:
            state.set('国自然官网返回错误，错误代码 {}'.format(ratify_info['code']))
        else:
            state.set('开始下载项目结题报告信息，请耐心等待...')
            try:
                download_state = nsfc_downloader.download(ratify)
                if download_state['success']:
                    state.set('下载完成，请在窗口中打开对应项目PDF')
                    nsfc.open_filepath(download_state['path'])
                else:
                    state.set('下载失败，原因： {}'.format(download_state['msg']))
            except Exception as e:
                state.set('软件错误，错误信息 {}'.format(e))

        # 删除临时文件夹
        shutil.rmtree(tmp_path)

    input_button = tk.Button(frm_main,
                             text="点击下载",
                             command=button_download
                             ).grid(row=1, column=3, padx=20)  # 输入框确定按钮

    # 第二栏
    tk.Label(frm_main, text="状态：").grid(row=2, column=1, pady=10)  # 输入提示
    state.set('暂无下载任务')
    state_label = tk.Label(frm_main,
                           textvariable=state
                           )
    state_label.grid(row=2, column=1, columnspan=3, pady=10)

    # 第三栏
    frm_info = tk.Frame(frm_main, pady=20)
    frm_info.grid(row=3, column=2)

    tk.Label(frm_info, text="相关信息：").grid(row=1, column=1, pady=10)  # 输入提示
    tk.Button(frm_info, text="项目说明",
              command=lambda: webbrowser.open('https://github.com/Rhilip/NSFC_conclusion_downloader')
              ).grid(row=1, column=2, padx=3)  # 输入提示
    tk.Button(frm_info, text="捐赠",
              command=lambda: webbrowser.open('https://blog.rhilip.info/')
              ).grid(row=1, column=3, padx=3)  # 输入提示

    window.mainloop()
