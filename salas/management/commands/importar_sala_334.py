import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from maquinas.models import Maquina
from salas.models import Sala


class Command(BaseCommand):
    help = "Importa as máquinas da Sala 334 a partir do CSV"

    def handle(self, *args, **options):
        csv_path = os.path.join(
            settings.BASE_DIR,
            "MacAddresses + Hostname + IPs - Máquinas NCC -_ FOG - Sala 334(1).csv",
        )

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {csv_path}"))
            return

        sala, created = Sala.objects.get_or_create(nome="334")
        if created:
            self.stdout.write(self.style.SUCCESS("Sala 334 criada"))
        else:
            self.stdout.write("Sala 334 já existe")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)

            macs = []
            criadas = 0
            ignoradas = 0

            for row in reader:
                if not row or not row[0].strip():
                    continue

                mac = row[0].strip()
                marca_patrimonio = row[1].strip()
                ip = row[3].strip() if len(row) > 3 else ""

                patrimonio = (
                    marca_patrimonio.split("_")[-1]
                    if "_" in marca_patrimonio
                    else marca_patrimonio
                )
                nome = f"lenovo-{patrimonio}"

                _, created = Maquina.objects.get_or_create(
                    mac_address=mac,
                    defaults={
                        "nome": nome,
                        "patrimonio": patrimonio,
                        "tipo_os": "debian",
                        "ultimo_ip": ip or None,
                    },
                )

                if created:
                    criadas += 1
                else:
                    ignoradas += 1

                macs.append(mac)

        maquinas = Maquina.objects.filter(mac_address__in=macs)
        sala.maquinas.add(*maquinas)

        self.stdout.write(
            self.style.SUCCESS(
                f"{criadas} máquinas criadas, {ignoradas} já existiam, "
                f"{maquinas.count()} associadas à Sala 334"
            )
        )
