# ---------------------------------------------------
# File Name: eval.py 
# Description: Owner-only code execution & shell commands
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import os
import re
import subprocess
import sys
import traceback
from inspect import getfullargspec
from io import StringIO
from time import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER_ID
from devgagan import app

async def aexec(code, client, message):
    """Execute async code safely"""
    exec(
        "async def __aexec(client, message): "
        + "".join(f"\n {a}" for a in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)

async def edit_or_reply(msg, **kwargs):
    """Edit if possible, else reply"""
    func = msg.edit_text if msg.from_user.is_self else msg.reply
    spec = getfullargspec(func.__wrapped__).args
    await func(**{k: v for k, v in kwargs.items() if k in spec})

@app.on_edited_message(
    filters.command(["evv", "evr"]) & filters.user(OWNER_ID)
)
@app.on_message(
    filters.command(["evv", "evr"]) & filters.user(OWNER_ID)
)
async def executor(client, message):
    """Execute Python code"""
    if len(message.command) < 2:
        return await edit_or_reply(message, text="❌ **No code provided!**")
    
    code = message.text.split(maxsplit=1)[1]
    start_time = time()
    
    # Redirect stdout/stderr
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    
    try:
        await aexec(code, client, message)
    except Exception:
        exc = traceback.format_exc()
    
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    # Build result
    evaluation = exc or stderr or stdout or "✅ Success"
    final_output = f"<b>📕 Result:</b>\n<pre language='python'>{evaluation}</pre>"
    
    # Handle large output
    if len(final_output) > 4096:
        filename = f"eval_{int(time())}.txt"
        with open(filename, "w+", encoding="utf8") as f:
            f.write(evaluation)
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏳", callback_data=f"runtime {time()-start_time:.3f}s")]])
        
        await message.reply_document(
            document=filename,
            caption=f"<b>🔗 Eval:</b> <code>{code[:980]}</code>\n\n<b>📕 Result:</b> Attached",
            reply_markup=keyboard,
        )
        await message.delete()
        os.remove(filename)
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏳", callback_data=f"runtime {time()-start_time:.3f}s"),
                InlineKeyboardButton("🗑", callback_data=f"forceclose abc|{message.from_user.id}"),
            ]
        ])
        await edit_or_reply(message, text=final_output, reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"runtime"))
async def runtime_func_cq(_, cq):
    runtime = cq.data.split(None, 1)[1]
    await cq.answer(runtime, show_alert=True)

@app.on_callback_query(filters.regex("forceclose"))
async def forceclose_command(_, callback_query):
    data = callback_query.data.split("|")
    if len(data) != 2 or callback_query.from_user.id != int(data[1]):
        return await callback_query.answer("❌ Not authorized!", show_alert=True)
    
    await callback_query.message.delete()
    try:
        await callback_query.answer()
    except:
        pass

@app.on_edited_message(filters.command("shll") & filters.user(OWNER_ID))
@app.on_message(filters.command("shll") & filters.user(OWNER_ID))
async def shellrunner(_, message):
    """Execute shell commands"""
    if len(message.command) < 2:
        return await edit_or_reply(message, text="❌ **Usage:** /shll `command`")
    
    cmd = message.text.split(maxsplit=1)[1]
    
    # Safely parse command
    if "\n" in cmd:
        # Multi-line commands
        commands = cmd.split("\n")
        full_output = ""
        for line in commands:
            if not line.strip():
                continue
            try:
                shell_parts = re.split(r' (?=(?:[^\'"]|\'[^\']*\'|"[^"]*")*$)', line)
                process = subprocess.Popen(
                    shell_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                full_output += f"▶️ {line}\n"
                full_output += stdout or stderr or "✅ Executed\n"
                full_output += "\n"
            except Exception as e:
                full_output += f"❌ Error: {str(e)}\n"
        output = full_output.strip()
    else:
        # Single command
        try:
            shell_parts = re.split(r' (?=(?:[^\'"]|\'[^\']*\'|"[^"]*")*$)', cmd)
            process = subprocess.Popen(
                shell_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            output = stdout or stderr or "✅ Executed"
        except Exception as e:
            output = f"❌ Error: {str(e)}"
    
    # Send output
    if not output:
        output = "✅ Command executed (no output)"
    
    if len(output) > 4096:
        filename = f"shell_{int(time())}.txt"
        with open(filename, "w+", encoding="utf8") as f:
            f.write(output)
        
        await message.reply_document(
            document=filename,
            caption=f"<b>🖥️ Shell Command:</b> <code>{cmd[:100]}</code>\n<b>📄 Result:</b> Attached",
        )
        os.remove(filename)
    else:
        await edit_or_reply(message, text=f"<b>🖥️ Output:</b>\n<pre>{output}</pre>")

@app.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart(_, message):
    """Restart the bot"""
    await message.reply("🔄 **Restarting bot...**")
    os.execl(sys.executable, sys.executable, "-m", "devgagan")
    