import os
from datetime import datetime

from quart import (
    Quart,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    websocket,
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import async_conn
from util import *


load_dotenv()

UPLOAD_FOLDER = 'uploads'
current_background = None
esp32_connected = False
auto_relay_on = True
relay_on = False
controller = async_conn.AsyncDeviceController()
scheduler = AsyncIOScheduler()

app = Quart(__name__, template_folder="html")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


async def switch_on():
    global relay_on
    relay_on = True
    await controller.send_control_action("LightON")


async def switch_off():
    global relay_on
    relay_on = False
    await controller.send_control_action("LightOFF")


async def daily_sun_job():
    if controller is None:
        return

    sunrise_t, sunset_t = get_sun_times()
    now = datetime.now(sunrise_t.tzinfo)

    if sunrise_t > now:
        scheduler.add_job(
            switch_off,
            trigger="date",
            run_date=sunrise_t,
            id="sunrise_job",
            replace_existing=True
        )
    if sunset_t > now:
        scheduler.add_job(
            switch_on,
            trigger="date",
            run_date=sunset_t,
            id="sunset_job",
            replace_existing=True
        )

    print(f"today: {now.strftime('%Y-%m-%d %H:%M:%S')}\n" \
          f"Sunrise: {sunrise_t.strftime('%Y-%m-%d %H:%M:%S')}\n" \
          f" Sunset: {sunset_t.strftime('%Y-%m-%d %H:%M:%S')}")


@app.before_serving
async def startup_scheduler():
    await daily_sun_job()

    scheduler.add_job(daily_sun_job, "cron", hour=0, minute=5, id="daily_sun_job")
    scheduler.start()


@app.after_serving
async def shutdown_scheduler():
    try:
        scheduler.shutdown()

    except Exception as e:
        print(e)


@app.websocket("/ws")
async def ws():
    return


@app.route("/")
async def index():
    global current_background
    files = get_files_in_dir(UPLOAD_FOLDER)
    current_background = files[0] if files else None

    return await render_template("index.html", bg_image=current_background,
                                               esp32_connected=esp32_connected,
                                               client_addr=controller.client_address if controller.client_address else "",
                                               auto_relay_on=auto_relay_on,
                                               relay_on=relay_on)


@app.route('/control', methods=['POST'])
async def control():
    global esp32_connected, auto_relay_on, relay_on
    form = await request.form

    if form.get("conn_op"):
        esp32_connected = not esp32_connected

        if esp32_connected:
            esp32_connected = await controller.start_conn(10)

        else:
            await controller.stop_server()
    
    elif form.get("auto_sw"):
        auto_relay_on = not auto_relay_on

        if auto_relay_on:
            scheduler.resume()
        else:
            scheduler.pause()

    elif form.get("light"):
        relay_on = not relay_on

        print(controller.connected)
        if controller.connected:
            if relay_on:
                await switch_on()
            else:
                await switch_off()
        else:
            return jsonify({
                "status": "error", 
                "message": "No active client connection"
            }), 200

    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
async def upload_image():
    if 'background_image' not in await request.files:
        return redirect(request.url)

    global current_background
    files = await request.files
    file = files['background_image']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], current_background)

        if current_background and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
                print(f"Delete Successful: {current_background}")
            except Exception as e:
                print(f"Fail to delete: {e}")

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        await file.save(file_path)

        current_background = filename

    return redirect(url_for('index'))


@app.route('/uploads/<filename>')
async def uploaded_file(filename):
    return await send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == "__main__":
    app.run(host="192.168.2.106", debug=True)
