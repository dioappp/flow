from django.core.management.base import BaseCommand
from hm.models import Operator
import pandas as pd


def add_arguments(self, parser):
    parser.add_argument(
        "--file",
        "-f",
        dest="file",
        action="store",
        type=str,
        help="Input lokasi file csv",
    )


def handle(self, *args, **options):
    file_loc = options.get("file")
    df = pd.read_csv(file_loc, sep=",")
