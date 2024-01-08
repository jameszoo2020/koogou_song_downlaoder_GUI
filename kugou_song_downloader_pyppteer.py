import tkinter as tk
from tkinter import messagebox
from tkinter.simpledialog import askinteger
import json
import time
import hashlib
import requests
import os
import asyncio
from pyppeteer import launch

headers = {
    'authority': 'complexsearch.kugou.com',
    'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
    'sec-ch-ua-mobile': '?0',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    'sec-ch-ua-platform': '"Windows"',
    'accept': '*/*',
    'sec-fetch-site': 'same-site',
    'sec-fetch-mode': 'no-cors',
    'sec-fetch-dest': 'script',
    'referer': 'https://www.kugou.com/',
    'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'cookie': 'kg_mid=1a8bf97ec26db1b38258848ec815e0a4',
}

def get_sign(params):
    string = ''
    for i in params:
        temp = i + '=' + params[i]
        string += temp
    string = 'NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt' + string + 'NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt'
    return hashlib.md5(string.encode(encoding='utf-8')).hexdigest().upper()

async def search_music(song_name, text_widget):
    search_results = []
    params = {'bitrate': '0',
              'callback': 'callback123',
              'clienttime': str(int(time.time() * 1000)),
              'clientver': '2000',
              'dfid': '-',
              'inputtype': '0',
              'iscorrection': '1',
              'isfuzzy': '0',
              'keyword': song_name,
              'mid': str(int(time.time() * 1000)),
              'page': '1',
              'pagesize': '30',
              'platform': 'WebFilter',
              'privilege_filter': '0',
              'srcappid': '2919',
              'tag': 'em',
              'token': '',
              'userid': '0',
              'uuid': str(int(time.time() * 1000)),
              }
    params['signature'] = get_sign(params)

    response = requests.get('https://complexsearch.kugou.com/v2/search/song', headers=headers, params=params)
    text = response.text[12:-2]
    search_data = json.loads(text)['data']['lists']

    for i, result in enumerate(search_data):
        music_list = {}
        music_list['FileName'] = result['FileName'].replace('<em>', '').replace('</em>', '')
        music_list['FileHash'] = result['FileHash']
        music_list['AlbumID'] = result['AlbumID']
        music_list['Duration'] = str(int(int(result['Duration']) / 60)) + '分' + str(
            (int(result['Duration']) - int(int(result['Duration']) / 60) * 60)) + '秒'
        result_str = f"{i + 1}. {music_list['FileName']} - {music_list['Duration']}\n"
        search_results.append(music_list)
        text_widget.insert(tk.END, result_str)  # Insert search results into the text widget

    return search_results

async def get_song_address(search_results, selected_index):
    if 1 <= selected_index <= len(search_results):
        filehash = search_results[selected_index - 1]['FileHash']
        album_id = search_results[selected_index - 1]['AlbumID']
        url = f'https://www.kugou.com/song/#hash={filehash}&album_id={album_id}'

        browser = await launch()
        page = await browser.newPage()
        await page.goto(url)
        await asyncio.sleep(1)  # Replace with await page.waitForSelector('#myAudio') for better waiting logic

        try:
            music_element = await page.querySelector('#myAudio')
            music_address = await page.evaluate('(element) => element.src', music_element)
        except Exception as e:
            print(f"Failed to get music address: {str(e)}")
            music_address = None

        await browser.close()

        return music_address
    else:
        return None

def get_song(music_address, song_name):
    with open('D:\\kugoumusic\\' + song_name + '.mp3', 'wb') as file:
        res = requests.get(music_address, headers=headers)
        file.write(res.content)

    # Open the folder after download
    folder_path = os.path.abspath('D:\\kugoumusic')
    os.system(f'explorer.exe {folder_path}')

class MusicDownloaderGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("音乐下载器")
        self.master.geometry('600x400')  # Increase window size

        self.label = tk.Label(master, text="请输入要下载的歌名：")
        self.label.pack()

        self.entry = tk.Entry(master)
        self.entry.pack()

        self.search_button = tk.Button(master, text="搜索", command=self.search_and_display_results)
        self.search_button.pack()

        self.result_text = tk.Text(master, height=10, width=60)
        self.result_text.pack()

        self.download_button = tk.Button(master, text="下载选中歌曲", command=self.download_selected_music)
        self.download_button.pack()

    def search_and_display_results(self):
        self.result_text.delete(1.0, tk.END)  # Clear the text widget

        song_name = self.entry.get()
        if not song_name:
            messagebox.showerror("错误", "请输入歌名")
            return

        try:
            loop = asyncio.get_event_loop()
            search_results = loop.run_until_complete(search_music(song_name, self.result_text))
            if not search_results:
                messagebox.showinfo("提示", "未找到相关歌曲")
                return

            selected_index = askinteger("选择下载", f"请输入要下载的歌曲序号 (1-{len(search_results)}):", minvalue=1,
                                        maxvalue=len(search_results))
            if selected_index:
                music_address = loop.run_until_complete(get_song_address(search_results, selected_index))
                if music_address:
                    get_song(music_address, song_name)
                    messagebox.showinfo("提示", f"{song_name} 下载完成！歌曲存放在D:\\kugoumusic")
                else:
                    messagebox.showinfo("提示", "无效的歌曲序号")

        except Exception as e:
            messagebox.showerror("错误", f"搜索失败: {str(e)}")

    def download_selected_music(self):
        song_name = self.entry.get()

        results_text = self.result_text.get(1.0, tk.END)

        if results_text.strip():
            try:
                search_results = []
                for line in results_text.split('\n'):
                    if line.strip():
                        parts = line.split('.')
                        index = int(parts[0].strip())
                        music_info = parts[1].strip().split('-')
                        music_list = {
                            'FileName': music_info[0].strip(),
                            'FileHash': music_info[1].strip(),
                            'AlbumID': music_info[2].strip(),
                        }
                        search_results.append(music_list)

                if not search_results:
                    messagebox.showinfo("提示", "未找到相关歌曲")
                    return

                loop = asyncio.get_event_loop()
                selected_index = askinteger("选择下载", f"请输入要下载的歌曲序号 (1-{len(search_results)}):",
                                            minvalue=1, maxvalue=len(search_results))
                if selected_index:
                    music_address = loop.run_until_complete(get_song_address(search_results, selected_index))
                    if music_address:
                        get_song(music_address, song_name)
                        messagebox.showinfo("提示", f"{song_name} 下载完成！歌曲存放在D:\\kugoumusic")
                    else:
                        messagebox.showinfo("提示", "无效的歌曲序号")
            except Exception as e:
                messagebox.showerror("错误", f"下载失败: {str(e)}")
        else:
            messagebox.showinfo("提示", "请先进行搜索")


if __name__ == '__main__':
    root = tk.Tk()
    app = MusicDownloaderGUI(root)
    root.mainloop()
