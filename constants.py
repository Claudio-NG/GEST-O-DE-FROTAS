from PyQt6.QtGui import QColor

USERS_FILE = 'users.csv'
MODULES = [
    "Combustível",
    "Condutores",
    "Infrações e Multas",
    "Acidentes",
    "Avarias Corretivas (Acidentes e Mau Uso)",
    "Relatórios"
]
MULTAS_ROOT = r"T:\Veiculos\VEÍCULOS - RN\MULTAS"
GERAL_MULTAS_CSV = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS\GERAL_MULTAS.csv"
ORGAOS = ["DETRAN","DEMUTRAM","STTU","DNIT","PRF","SEMUTRAM","DMUT"]
MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
PORTUGUESE_MONTHS = {1:"JANEIRO",2:"FEVEREIRO",3:"MARÇO",4:"ABRIL",5:"MAIO",6:"JUNHO",7:"JULHO",8:"AGOSTO",9:"SETEMBRO",10:"OUTUBRO",11:"NOVEMBRO",12:"DEZEMBRO"}
DATE_FORMAT = "dd-MM-yyyy"
DATE_COLS = ["DATA INDICAÇÃO", "BOLETO", "SGU"]
STATUS_OPS = ["", "Pendente", "Pago", "Vencido"]
STATUS_COLOR = {"Pago": QColor("#2ecc71"), "Pendente": QColor("#ffd166"), "Vencido": QColor("#ef5350")}
PASTORES_DIR = r"T:\Veiculos\VEÍCULOS - RN\CPO-VEÍCULOS"
