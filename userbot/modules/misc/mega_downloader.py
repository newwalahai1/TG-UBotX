# Adapted from https://github.com/adekmaulana/OpenUserBot

from asyncio import create_subprocess_shell as asyncSubprocess
from asyncio.subprocess import PIPE as asyncPIPE

import asyncio
import re
import json
import os
import multiprocessing
import errno

from pySmartDL import SmartDL
from urllib.error import HTTPError
from os.path import exists

from ..help import add_help_item
from userbot import LOGS
from userbot.events import register
from userbot.modules.misc.upload_download import humanbytes


async def subprocess_run(megadl, cmd):
    subproc = await asyncSubprocess(cmd, stdout=asyncPIPE, stderr=asyncPIPE)
    stdout, stderr = await subproc.communicate()
    exitCode = subproc.returncode
    if exitCode != 0:
        await megadl.edit(
            '**An error was detected while running subprocess**\n'
            f'```exitCode: {exitCode}\n'
            f'stdout: {stdout.decode().strip()}\n'
            f'stderr: {stderr.decode().strip()}```')
        return exitCode
    return stdout.decode().strip(), stderr.decode().strip(), exitCode


async def mega_downloader_fallback(megadl, link):
    if not exists('mega'):
        os.mkdir('mega')
    await megadl.edit('`Downloading...`')
    cmd = f'megadl --path mega {link} > /dev/null'
    result = await subprocess_run(megadl, cmd)
    if result[2] != 0:
        return
    with open('list.txt', 'w+') as list_files:
        for downloaded_files in os.listdir('mega'):
            list_files.write(downloaded_files + '\n')
    result = open('list.txt', 'r').read()
    if len(result) >= 4096:
        await megadl.client.send_file(
            megadl.chat_id,
            "list.txt",
            reply_to=megadl.id,
            caption="`List files is too many, sending it as a file`",
         )
    else:
        await megadl.edit(f'**Downloaded files**:\n`{result}`')
    result.close()
    os.remove('list.txt')
    return


@register(outgoing=True, pattern=r"^\.mega(?: |$)(.*)")
async def mega_downloader(megadl):
    await megadl.edit("`Processing...`")
    msg_link = await megadl.get_reply_message()
    link = megadl.pattern_match.group(1)
    if link:
        pass
    elif msg_link:
        link = msg_link.text
    else:
        await megadl.edit("Usage: `.mega <MEGA.nz link>`")
        return
    try:
        link = re.findall(r'\bhttps?://.*mega.*\.nz\S+', link)[0]
    except IndexError:
        await megadl.edit("`No MEGA.nz link found`\n")
        return
    if "#F" in link:
        await megadl.edit('`MEGA.nz link is a folder...`')
        await asyncio.sleep(2)
        await mega_downloader_fallback(megadl, link)
        return
    cmd = f'bin/megadown -q -m {link}'
    result = await subprocess_run(megadl, cmd)
    try:
        data = json.loads(result[0])
    except json.JSONDecodeError:
        await megadl.edit("`Error: Can't extract the link`\n")
        return
    except TypeError:
        return
    except IndexError:
        return
    file_name = data["file_name"]
    file_url = data["url"]
    hex_key = data["hex_key"]
    hex_raw_key = data["hex_raw_key"]
    temp_file_name = file_name + ".temp"
    downloaded_file_name = "./" + "" + temp_file_name
    downloader = SmartDL(
        file_url, downloaded_file_name, progress_bar=False)
    display_message = None
    try:
        downloader.start(blocking=False)
    except HTTPError as e:
        await megadl.edit("`" + str(e) + "`")
        return
    while not downloader.isFinished():
        status = downloader.get_status().capitalize()
        total_length = downloader.filesize if downloader.filesize else None
        downloaded = downloader.get_dl_size()
        percentage = int(downloader.get_progress() * 100)
        progress = downloader.get_progress_bar()
        speed = downloader.get_speed(human=True)
        estimated_total_time = downloader.get_eta(human=True)
        try:
            current_message = (
                "File Name:"
                f"\n`{file_name}`\n\n"
                "Status:"
                f"\n**{status}** | {progress} `{percentage}%`"
                f"\n{humanbytes(downloaded)} of {humanbytes(total_length)}"
                f" @ {speed}"
                f"\nETA: {estimated_total_time}"
            )
            if display_message != current_message:
                await megadl.edit(current_message)
                await asyncio.sleep(0.2)
                display_message = current_message
        except Exception:
            pass
        finally:
            if status == "Combining":
                await asyncio.sleep(float(downloader.get_eta()))
    if downloader.isSuccessful():
        download_time = downloader.get_dl_time(human=True)
        try:
            P = multiprocessing.Process(target=await decrypt_file(megadl,
                                        file_name, temp_file_name, hex_key, hex_raw_key),
                                        name="Decrypt_File")
            P.start()
            P.join()
        except FileNotFoundError as e:
            await megadl.edit(str(e))
            return
        else:
            await megadl.edit(f"`{file_name}`\n\n"
                              "Successfully downloaded\n"
                              f"Download took: {download_time}")
    else:
        await megadl.edit("`Failed to download, check heroku Logs for more details`")
        for e in downloader.get_errors():
            LOGS.info(str(e))
    return


async def decrypt_file(megadl, file_name, temp_file_name,
                       hex_key, hex_raw_key):
    cmd = ("cat '{}' | openssl enc -d -aes-128-ctr -K {} -iv {} > '{}'"
           .format(temp_file_name, hex_key, hex_raw_key, file_name))
    if await subprocess_run(megadl, cmd):
        os.remove(temp_file_name)
    else:
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), file_name)
    return


add_help_item(
    "megadown",
    "Misc",
    "UserBot module to download files from MEGA.nz",
    """
    `.mega <mega url>`
    **Usage:** Reply to a MEGA.nz link or paste your MEGA.nz link to
    download the file into your userbot server.
    """
)
