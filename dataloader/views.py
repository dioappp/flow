import asyncio
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.management import call_command


@login_required
def index(request):
    return render(request, "dataloader/index.html")


async def ritase(request):
    date = request.POST.get("date")
    hour = request.POST.get("hour")
    durasi = request.POST.get("durasi")
    date_str = f"{date} {hour}"

    if durasi == "":
        durasi = 1

    def run_command():
        call_command("ritase", date=date_str, durasi=durasi)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_command)
    return HttpResponse(status=204)


async def hm(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))

    def run_command():
        call_command("hm", date=date, shift=shift)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_command)
    return HttpResponse(status=204)
