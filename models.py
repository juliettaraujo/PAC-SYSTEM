from datetime import datetime

class Circuit:
    def __init__(
    self,
    id=None,
    name="",
    nomenclature="",
    voltage=13.8,
    block="A",
    amps=0.0,
    status="ACTIVO",
    start_time="",
    end_time="",
    duration="",
    mw=0.0,
    pac=0,
    is_consigned=0,
    last_outage_duration=0
):

        self.id = id
        self.name = name
        self.nomenclature = nomenclature
        self.voltage = float(voltage)
        self.block = block
        self.amps = float(amps)
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.pac = pac
        self.is_consigned = is_consigned
        self.last_outage_duration = last_outage_duration

        # CALCULO MW
        self.mw = self.calculate_mw()

        # TIEMPO EN VIVO
        self.outage_time = self.calculate_outage_time()

    def calculate_mw(self):
        factor = 0.02 if self.voltage == 13.8 else 0.05
        return round(self.amps * factor, 2)

    @staticmethod
    def calculate_duration(start, end):
        if not start or not end: return "0 min"
        try:
            # Formato 24h para el cálculo
            fmt = '%H:%M'
            t1 = datetime.strptime(start, fmt)
            t2 = datetime.strptime(end, fmt)
            diff = int((t2 - t1).total_seconds())
            if diff < 0: diff += 86400
            return f"{diff // 60} min"
        except: return "0 min"

    def calculate_outage_time(self):

        # Si está activo no mostramos tiempo
        if self.status == 'ACTIVO':
            return '--'

        # Si no hay hora de inicio
        if not self.start_time:
            return '--'

        try:

            fmt = '%H:%M'

            start = datetime.strptime(self.start_time, fmt)
            now = datetime.now()

            current = datetime.strptime(
                now.strftime('%H:%M'),
                fmt
            )

            diff = int((current - start).total_seconds())

            # Cruce de medianoche
            if diff < 0:
                diff += 86400

            hours = diff // 3600
            minutes = (diff % 3600) // 60

            return f'{hours:02}h {minutes:02}m'

        except:
            return '--'