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
    parse = argparse.ArgumentParser(
        description='A tool to Download PDF format conclusion from http://output.nsfc.gov.cn/')
    parse.add_argument('--ratify', '-r', help='The ratify id of the project you want to download', required=True)
    parse.add_argument('--tmp_path', '-t', default='./tmp', help='The path you want to save tmp file')
    parse.add_argument('--out_path', '-o', default='./output', help='The path you want to save output PDF file')
    return parse.parse_args()


def mkdir_p(path, mode=0o777):
    """
    创建文件夹

    :param path:
    :param mode:
    :return:
    """
    try:
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
    debug = True
    ratify_info = {}

    def __init__(self, tmp_path, out_path):
        self.tmp_path = tmp_path
        self.out_path = out_path

        # 使得相关文件夹存在
        mkdir_p(tmp_path)
        mkdir_p(out_path)

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
        except requests.HTTPError as e:
            rj = {'success': False, 'code': r.status_code}
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

        i = 1
        while True:
            tmp_file = os.path.join(self.tmp_path, '{}_{}.png'.format(ratify, i))
            if os.path.exists(tmp_file):
                content = open(tmp_file, 'rb').read()
            else:
                req_url = "http://output.nsfc.gov.cn/report/{}/{}_{}.png".format(ratify_prefix, ratify, i)
                print('正在请求页面 {}'.format(req_url))
                r = requests.get(req_url, timeout=10)
                if r.status_code == 404:
                    break
                content = r.content
                with open(tmp_file, 'wb') as tmp_f:
                    tmp_f.write(r.content)

            img_files_list.append(tmp_file)
            img_bytes_list.append(content)
            i += 1

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
                status['msg'] = 'PDF已存在，请打开 `{}`。'.format(status['path'])
            else:
                print('开始下载 {} {}'.format(ratify, project_name))
                img_files_list, img_bytes_list = self.download_loop(ratify)
                print('下载完成 {} {}'.format(ratify, project_name))

                if len(img_bytes_list) > 0:
                    print('正在组合PDF {}'.format(status['path']))
                    pdf = img2pdf.convert(img_bytes_list)
                    with open(status['path'], "wb") as file_:
                        file_.write(pdf)
                        status['success'] = True

                    print('移除临时文件')
                    for f in img_files_list:
                        os.remove(f)
                else:
                    status['msg'] = '下载过程出现问题，未获得有效图片。'

        if status['msg']:
            print(status['msg'])

        return status


if __name__ == '__main__':
    args = arg_parser()
    downloader = NsfcDownloader(args.tmp_path, args.out_path)
    downloader.download(args.ratify)
