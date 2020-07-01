import os
import re
import json
import argparse
import errno

import img2pdf
import requests

__VERSION__ = 'v0.1.0'
__AUTHOR__ = 'Rhilip'


def arg_parser():
    parser = argparse.ArgumentParser(
        description='A tool to Download PDF format conclusion from http://output.nsfc.gov.cn/'
    )
    parser.add_argument('--version', '-v', action='version', version=__VERSION__)
    parser.add_argument('--ratify', '-r', help='The ratify id of the project you want to download', required=True)
    parser.add_argument('--tmp_path', '-t', default='./tmp', help='The path you want to save tmp file')
    parser.add_argument('--out_path', '-o', default='./output', help='The path you want to save output PDF file')
    parser.add_argument('--no-debug', dest='debug', action='store_false', help='Disable The debug mode')
    parser.set_defaults(debug=True)
    return parser.parse_args()


def mkdir_p(path, mode=0o777):
    """
    创建文件夹

    :param path:
    :param mode:
    :return:
    """
    try:
        path = os.path.abspath(path)
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def open_filepath(path):
    try:
        os.startfile(path)
    except Exception:
        pass


def clean_filename(string: str) -> str:
    """
    清理文件名中的非法字符，防止保存到文件系统时出错

    :param string:
    :return:
    """
    string = string.replace(':', '_').replace('/', '_').replace('\x00', '_')
    string = re.sub('[\n\\\*><?\"|\t]', '', string)
    return string.strip()


class NsfcDownloader:
    i = 1
    download_finish = False
    download_stats = {}

    debug = True
    ratify_info = {}

    def __init__(self, out_path, tmp_path):
        self.out_path = out_path
        self.tmp_path = tmp_path

        # 使得相关文件夹存在
        mkdir_p(out_path)
        mkdir_p(tmp_path)

    def clear_state(self):
        self.i = 1
        self.download_finish = False
        self.download_stats = {}

    def get_ratify_info_from_nsfc(self, ratify) -> dict:
        """
        从官网获取信息

        :param ratify: 申请号
        :return:
        """
        r = requests.get('http://output.nsfc.gov.cn/baseQuery/data/conclusionProjectInfo/{}'.format(ratify))

        try:
            r.raise_for_status()
            rj = r.json()  # project_info
            rj['success'] = True
        except Exception as e:
            rj = {'success': False, 'msg': str(e)}
            # Debug 模式下重新抛出抛出
            if self.debug:
                raise e

        return rj

    def get_ratify_info(self, ratify) -> dict:
        # 检查对象内是不是有缓存
        if ratify not in self.ratify_info:
            # 检查本地目录是不是有缓存
            project_info_file = os.path.join(self.tmp_path, '{}.json'.format(ratify))
            if os.path.exists(project_info_file):
                rj = json.load(open(project_info_file, 'r', encoding='utf-8'))
            else:
                rj = self.get_ratify_info_from_nsfc(ratify)

            # 存入对象缓存
            self.ratify_info[ratify] = rj

        return self.ratify_info[ratify]

    def download_loop(self, ratify) -> tuple:
        """
        下载核心方法

        :param ratify:
        :return:
        """
        img_files_list = []
        img_bytes_list = []

        ratify_prefix = ratify[:2]

        self.i = 1
        while True:
            tmp_file = os.path.join(self.tmp_path, '{}_{}.png'.format(ratify, self.i))
            if os.path.exists(tmp_file):
                content = open(tmp_file, 'rb').read()
            else:
                req_url = "http://output.nsfc.gov.cn/report/{}/{}_{}.png".format(ratify_prefix, ratify, self.i)
                print('正在请求页面 {}'.format(req_url))
                r = requests.get(req_url, timeout=10)
                if r.status_code == 404:
                    break
                content = r.content

                if self.debug:
                    with open(tmp_file, 'wb') as tmp_f:
                        tmp_f.write(r.content)

            img_files_list.append(tmp_file)
            img_bytes_list.append(content)
            self.i += 1

        self.download_finish = True

        return img_files_list, img_bytes_list

    def download(self, ratify):
        status = {'success': False, 'msg': ''}
        print('开始获取项目信息，项目编号： {}'.format(ratify))

        ratify_info = self.get_ratify_info(ratify)
        if ratify_info.get('code') != 200 or 'data' not in ratify_info:
            status['msg'] = '项目可能不存在，请重新检查网页 http://output.nsfc.gov.cn/conclusionProject/{} 显示'.format(ratify)
        else:
            project_name = ratify_info['data'].get('projectName', '')
            status['path'] = os.path.join(self.out_path, clean_filename('{} {}.pdf'.format(ratify, project_name)))

            if os.path.exists(status['path']):
                status['success'] = True
                status['msg'] = 'PDF已存在，请打开 `{}`。'.format(status['path'])
            else:
                try:
                    print('开始下载 {} {}'.format(ratify, project_name))
                    img_files_list, img_bytes_list = self.download_loop(ratify)
                    print('下载完成 {} {}'.format(ratify, project_name))

                    if len(img_bytes_list) > 0:
                        print('正在组合PDF {}'.format(status['path']))
                        pdf = img2pdf.convert(img_bytes_list)
                        with open(status['path'], "wb") as file_:
                            file_.write(pdf)
                            status['success'] = True

                        if self.debug:
                            print('移除临时文件')
                            for f in img_files_list:
                                os.remove(f)
                    else:
                        status['msg'] = '下载过程出现问题，未获得有效图片。'
                except Exception as e:
                    status['msg'] = '内部错误： {}'.format(e)

        if status['msg']:
            print(status['msg'])

        self.download_stats = status
        return self.download_stats


if __name__ == '__main__':
    args = arg_parser()
    downloader = NsfcDownloader(args.out_path, args.tmp_path)
    downloader.download(args.ratify)
