from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import time
import snap7
import sys
import mysql.connector

from mysql.connector import Error

from stack import Ui_MainWindow

ID_POSTAJE = 1                                      # vsaka postaja potrebuje svoj ID
UPORABNIK = 8372                                    # DOKLER NI POŠLIHTANA IDENTIFIKACIJA/AVTENTIKACIJA

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('Aplikacija kolo')
        self.stackedWidget.setCurrentIndex(0)
        self.stackedWidget_2.setCurrentIndex(0)
        time.sleep(0.01)

        # mysql komunikacaija PC to server
        self.trigDatabase = True
        try:
            self.mydb = mysql.connector.connect(
                host='192.168.0.2',
                user='jkovse',
                passwd='6KVD646c.',
                database='sys',
                auth_plugin='mysql_native_password'  # moja avtentikacija je native password, ki jo moram
                # tukaj določiti; default je caching_sha2_password
            )
            if self.mydb.is_connected():
                db_info = self.mydb.get_server_info()
                print('halo halo: ', db_info)
                self.mycursor = self.mydb.cursor()
                self.mycursor.execute('select database();')
                record = self.mycursor.fetchone()
                print('connected to: ', record)
        except Error as e:
            print('Error while connecting to MySQL database: ', e)

        # snap7 komunikacija s PLK
        try:
            self.client = snap7.client.Client()
            self.client.connect('192.168.0.1', 0, 1)
            print('connected: ', self.client.get_connected())
        except:
            print('connected: ', self.client.get_connected())

        # ura
        timer = QTimer(self)
        timer.timeout.connect(self.clock)
        timer.start(1000)

        # tipke prva stran
        self.btn_sposodi.pressed.connect(lambda: self.sposodiScreen())
        self.btn_vrni.pressed.connect(lambda: self.vrniScreen())
        self.btn_informacije.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(3))
        self.btn_rezerviraj.pressed.connect(lambda: self.rezervirajScreen(1))

        # tipke nazaj
        btn_nazaj = [self.btn_nazaj0, self.btn_nazaj1, self.btn_nazaj2, self.btn_nazaj3]
        for n in range(len(btn_nazaj)):
            btn_nazaj[n].pressed.connect(self.ponastaviIndeks)

        #   #   #   #   tipke stran izposodi si   #   #   #   #

        self.kolo1prisotno.pressed.connect(lambda: self.funkcija(1))
        self.kolo2prisotno.pressed.connect(lambda: self.funkcija(2))
        self.kolo1niprisotno.pressed.connect(lambda: self.funkcija(3))
        self.kolo2niprisotno.pressed.connect(lambda: self.funkcija(4))

        row = 4
        col = 4                                                         # prilagodljiv grid layout
        st = 1                                                          # spreminja se glede na št gumbov
        self.btn = [None] * 16
        for k in range(row):
            for l in range(col):
                self.btn[st-1] = QPushButton('%s' %st)        # PAZI index tipke za ena manjši od št napisanega na tipki
                self.btn[st-1].pressed.connect(lambda st=st: self.sposodiKolo(st))
                self.btn[st-1].setStyleSheet('background-color:#0CB1E8;\ncolor: #ffffff;\nborder-radius:15%;\n'
                                             'position:absolute;\nmargin:5px 10px 5px 10px;\nheight:50px;\n'
                                             'font: 16px bold;\n')
                self.sposodiLayout.addWidget(self.btn[st-1], k, l)
                st += 1
        #   #   #   #   vrni kolo   #   #   #   #
        st = 1  # spreminja se glede na št gumbov
        self.btn_vrni = [None] * 16
        for k in range(row):
            for l in range(col):
                self.btn_vrni[st - 1] = QPushButton('%s' % st)  # PAZI index tipke za ena manjši od št napisanega na tipki
                self.btn_vrni[st - 1].pressed.connect(lambda st=st: self.vrniKolo(st))
                self.btn_vrni[st - 1].setStyleSheet('background-color:#0CB1E8;\ncolor: #ffffff;\nborder-radius:15%;\n'
                                               'position:absolute;\nmargin:5px 10px 5px 10px;\nheight:50px;\n'
                                               'font: 16px bold;\n')
                self.sposodiLayout.addWidget(self.btn_vrni[st - 1], k, l)
                st += 1

        #   #   #   #   rezerviraj stebriček tipke   #   #   #   #
        self.btn_stebricek = [None] * 16
        st = 1
        for k in range(row):
            for l in range(col):
                self.btn_stebricek[st-1] = QPushButton('%s' %st)
                self.btn_stebricek[st-1].pressed.connect(lambda st=st: self.rezerviraj(st))
                self.btn_stebricek[st-1].setStyleSheet('background-color:#0CB1E8;\ncolor: #ffffff;\nborder-radius:15%;\n'
                                                      'position:absolute;\nmargin:5px 10px 5px 10px;\nheight:50px;\n'
                                                      'font: 16px bold;\n')
                self.gridLayoutRezerviraj.addWidget(self.btn_stebricek[st-1], k, l)
                st += 1
        # stran: informacije
        stPostaj = 4
        btn_postaja = [self.btn_postaja1, self.btn_postaja2, self.btn_postaja3, self.btn_postaja4]

        for m in range(stPostaj):
            btn_postaja[m].pressed.connect(lambda m=m: self.kateraTabela(m+1))
            # ustvari ustrezno tabelo, ki jo želimo videti

        #   #   #   #   geslo   #   #   #   #
        self.password.setEchoMode(QLineEdit.Password)           # znaki gesla kot ***
        self.pushButton.pressed.connect(lambda: self.kdoVpisan())
        # parametri koles pri 'moji' postaji
        self.kolesa = [0 for i in range(16)]                    # v katerem steričku je kolo parkirano
        self.stStebrickov = self.client.db_read(3, 4, 2)
        self.idPosameznegaKolesa = ['' for i in range(16)]
        self.tipPosameznegaKolesa = ['' for i in range(16)]
        self.posameznaBaterija = ['' for i in range(16)]
        self.database = [self.idPosameznegaKolesa, self.tipPosameznegaKolesa, self.posameznaBaterija]
        self.preberiParametre()
        print('database: %s' %self.database[0] + '\n          %s' %self.database[1] + '\n          %s' %self.database[2] )

        # array za 'druge' postaje
        self.tabelaSQL = [['' for i in range(16)],['' for j in range(16)] ,['' for k in range(16)], [int for m in range(16)]]
        self.flag = [False for i in range(16)]
        #   #   #   #   # funkcije #   #   #   #   #


    def funkcija(self, i):
        prisotnost = self.client.db_read(1, 6, 2)
        print(prisotnost)
        if i == 1:
            prisotnost[0] |= 1
            self.kolo1prisotno.setStyleSheet('background-color:green;')
            self.kolo1niprisotno.setStyleSheet('background-color:#0CB1E8;')
        if i == 2:
            prisotnost[0] |= 2
            self.kolo2prisotno.setStyleSheet('background-color:green;')
            self.kolo2niprisotno.setStyleSheet('background-color:#0CB1E8;')
        if i == 3:
            prisotnost[0] &= 254
            self.kolo1prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo1niprisotno.setStyleSheet('background-color:green;')
        if i == 4:
            prisotnost[0] &= 253
            self.kolo2prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo2niprisotno.setStyleSheet('background-color:green;')
        self.client.as_db_write(1, 6, prisotnost)

        # update tabele za postajo tega PLK-ja (vsako sekundo)
    def updateTabele(self):
        self.preberiParametre()
        insertTuple2 = (self.stStebrickov[ID_POSTAJE], self.stKoles[ID_POSTAJE], ID_POSTAJE)
        for i in range(16):
            insertTuple = (self.idPosameznegaKolesa[i], self.posameznaBaterija[i], i+1)
            try:
                self.mycursor.execute("UPDATE postaja1 SET idKolesa = %s, procentBaterije = %s WHERE stebricek = %s", insertTuple)
                self.mydb.commit()
                self.mycursor.execute("UPDATE celoten_sistem SET stStebrickov = %s, stKoles = %s WHERE idPostaje = %s", insertTuple2)
                self.mydb.commit()

            except:
                print('Error occured while updating %s row of table postaja1', i+1)
        # update v celosistemsko tabelo (kjer so vse postaje - št. stebričkov, št.koles itd)

    def preberiParametre(self):
        self.stStebrickov = self.client.db_read(3, 4, 2)
        self.idKoles = self.client.db_read(3, 6, self.stStebrickov[1] * 2)
        self.procentBaterije = self.client.db_read(3, 70, self.stStebrickov[1] * 2)
        self.stKoles = self.client.db_read(3, 102, 2)

        for i in range(16):
            vmesna = 0
            if i < self.stStebrickov[1]:
                for j in range(2):
                    if j == 1:
                        vmesna += self.idKoles[(i * 2) + j]
                        self.idPosameznegaKolesa[i] = str(vmesna)
                    else:
                        vmesna = (256 * self.idKoles[(i * 2) + j])
                if vmesna > 250:
                    self.tipPosameznegaKolesa[i] = 'električno kolo'
                    self.posameznaBaterija[i] = str(self.procentBaterije[(i * 2) + j]) + ' %'
                elif vmesna != 0:
                    self.tipPosameznegaKolesa[i] = 'goni poni'
                    self.posameznaBaterija[i] = 'ni baterije'
                else:
                    self.tipPosameznegaKolesa[i] = 'prazno'
                    self.posameznaBaterija[i] = 'prazno'
            else:
                self.idPosameznegaKolesa[i] = 'n/a'
                self.tipPosameznegaKolesa[i] = 'n/a'
                self.posameznaBaterija[i] = 'n/a'
            insertTuple = (self.tipPosameznegaKolesa[i], i+1)
            self.mycursor.execute("UPDATE postaja1 SET tipKolesa = %s WHERE stebricek = %s", insertTuple)               # dodaj še tip kolesa
            self.mydb.commit()
        # print(self.database)

    # preberi parametre 'drugih' in jih zapiši v tabelo na PC-ju
    def kateraTabela(self, idPostaje):
        self.preberiSQL(idPostaje)
        self.informacijeTabela1.setRowCount(self.stKolesPostajaX + 1)
        self.informacijeTabela1.setColumnCount(3)
        self.informacijeTabela1.setItem(0, 0, QTableWidgetItem('Postaja %s' % idPostaje))
        k = 0
        for i in range(self.stStebrickovPostajaX):
            if self.tabelaSQL[0][i] != '0':
                k += 1
                for j in range(3):
                    self.informacijeTabela1.setItem(k, j, QTableWidgetItem(self.tabelaSQL[j][i]))
        self.stackedWidget_2.setCurrentIndex(1)

    # prebere podatke katerekoli postaje iz SQL serverja
    def preberiSQL(self, idPostaje):
        query1 = 'SELECT * FROM celoten_sistem WHERE idPostaje = %s'
        query2 = 'SELECT * FROM postaja' + str(idPostaje)
        self.mycursor.execute(query1, (idPostaje,))
        stKolesPostajaX = self.mycursor.fetchall()
        self.stKolesPostajaX = stKolesPostajaX[0][2]
        self.stStebrickovPostajaX = stKolesPostajaX[0][1]
        self.mycursor.execute(query2)
        podatkiPostajaX = self.mycursor.fetchall()
        #print(podatkiPostajaX)
        for i in range(16):
            self.tabelaSQL[0][i] = podatkiPostajaX[i][1]    # id kolesa
            self.tabelaSQL[1][i] = podatkiPostajaX[i][2]    # procent baterije
            self.tabelaSQL[2][i] = podatkiPostajaX[i][3]    # tip kolesa
            self.tabelaSQL[3][i] = podatkiPostajaX[i][4]    # user id, ki je rezerviral
        if idPostaje == ID_POSTAJE:
            self.preveriRezervacije()

    def sposodiKolo(self, indexKolesa):
        self.enable = indexKolesa.to_bytes(2, 'big')        #enable unlock
        #print(self.parametriKolesa)
        #
        #
        #
        #
        #
        ###TO DO
        # pogoj, če rezervirano kolo lahko enablam samo če sem pravi user
        #
        #
        #
        #

        self.client.as_db_write(1, 0, self.enable)

        self.ponastaviIndeks()

    def vrniKolo(self, indexKolesa):
        self.disable = indexKolesa.to_bytes(2, 'big')       #disable unlock
        self.client.as_db_write(1, 2, self.disable)

        self.ponastaviIndeks()

    def clock(self):
        self.updateTabele()
        self.preberiSQL(ID_POSTAJE)             # vsako sekundo beri ali je kdo slučajno rezerviral stebriček na tej postaji
        self.time = QTime.currentTime()
        self.text = self.time.toString('hh:mm:ss')
        self.dateTimeLabel.setText(self.text)
        # to daš potem ven ###
        if self.client.db_read(1, 6, 2)[0] == 1:
            self.kolo1prisotno.setStyleSheet('background-color:green;')
            self.kolo1niprisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo2prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo2niprisotno.setStyleSheet('background-color:green')
        elif self.client.db_read(1, 6, 2)[0] == 2:
            self.kolo1prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo1niprisotno.setStyleSheet('background-color:green;')
            self.kolo2prisotno.setStyleSheet('background-color:green;')
            self.kolo2niprisotno.setStyleSheet('background-color:#0CB1E8;')
        elif self.client.db_read(1, 6, 2)[0] == 3:
            self.kolo1prisotno.setStyleSheet('background-color:green;')
            self.kolo1niprisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo2prisotno.setStyleSheet('background-color:green;')
            self.kolo2niprisotno.setStyleSheet('background-color:#0CB1E8;')
        elif self.client.db_read(1, 6, 2)[0] == 0:
            self.kolo1prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo1niprisotno.setStyleSheet('background-color:green;')
            self.kolo2prisotno.setStyleSheet('background-color:#0CB1E8;')
            self.kolo2niprisotno.setStyleSheet('background-color:green;')

        if self.client.db_read(3, 104, 4)[2] != 0:
            self.stebricek1rezerviran.setStyleSheet('background-color:green;')
        elif self.client.db_read(3, 104, 4)[0] == 0:
            self.stebricek1rezerviran.setStyleSheet('background-color:#0CB1E8;')
        if self.client.db_read(3, 108, 4)[2] != 0:
            self.stebricek2rezerviran.setStyleSheet('background-color:green;')
        elif self.client.db_read(3, 108, 4)[0] == 0:
            self.stebricek2rezerviran.setStyleSheet('background-color:#0CB1E8;')


    def ponastaviIndeks(self):
        self.stackedWidget.setCurrentIndex(0)
        self.stackedWidget_2.setCurrentIndex(0)

    #   #   #   # rezerviraj #  #   #   #
    def rezervirajScreen(self, idPostaje):
        # zaenkrat tole potem update-aj
        self.prisotnostKolesa()
        print(self.kolesa)
        for i in range(16):
            if self.kolesa[i] == 0 and (i < 2):     # pogleda samo 'svojo' bazo
                self.btn_stebricek[i].show()
            else:
                self.btn_stebricek[i].hide()
        self.stackedWidget.setCurrentIndex(6)
        #   #   #   #   #   #   #   #
        #self.preberiSQL(idPostaje)
        #self.ustvariTipkeRezerviraj(idPostaje)
        #self.postaja = idPostaje                    # katera postaja se gleda,

    def rezerviraj(self, stebricek):
        print(stebricek)
        # spet gledam samo svojo bazo update later #
        if stebricek == 1:
            self.client.as_db_write(3, 104, UPORABNIK.to_bytes(4, 'big'))
        elif stebricek == 2:
            self.client.as_db_write(3, 108, UPORABNIK.to_bytes(4, 'big'))
        #query = 'UPDATE postaja' + str(self.postaja) + ' SET userID = %s WHERE stebricek = %s'
        #self.mycursor.execute(query, (UPORABNIK, stebricek))
        #self.mydb.commit()
        #self.client.as_db_write(3, 168, stebricek.to_bytes(2, 'big'))                                                   # kateri stebricek rezervirati
        self.stackedWidget.setCurrentIndex(0)

    def ustvariTipkeRezerviraj(self, idPostaje):
        #print(self.tabelaSQL)
        for i  in range(16):
            if self.tabelaSQL[3][i] != 0 or self.tabelaSQL[0][i] != '0':
                self.btn_stebricek[i].hide()
            else:
                self.btn_stebricek[i].show()

        self.stackedWidget.setCurrentIndex(6)

    # izvede se ko klikneš katero postajo bi red rezerviral
    def preveriRezervacije(self):                                                   # PAZI! ko nekdo rezervira ali poteče timer se v tia db tisto polje postavi na  -1
        rezPrekinjena = self.client.db_read(3, 104, self.stStebrickov[1]*4)
        zero = int(0).to_bytes(4, 'big')
        for i in range(self.stStebrickov[1]):
            if rezPrekinjena[i*4] == 255:                                           # če timer potekel zapiši v db in v tabelo 0
                self.flag[i] = False
                self.client.as_db_write(3, 104 + (i*4), zero)
                self.mycursor.execute("UPDATE postaja1 SET userID = %s WHERE stebricek = %s", (0, i+1))
                self.mydb.commit()
            if self.tabelaSQL[3][i] != 0 and self.flag[i] == False:
                self.flag[i] = True
                self.client.as_db_write(3, 104+(i*4), self.tabelaSQL[3][i].to_bytes(4, 'big'))
                #self.client.as_db_write(3, 168, i.to_bytes(4, 'big'))

    def kdoVpisan(self):                    # login
        if self.username.text() == 'uporabnik' and self.password.text() == '1234':
            self.stackedWidget.setCurrentIndex(0)
        else:
            print('incorrect username or password:(')

    def prisotnostKolesa(self):                                         # preveri kateri stebrički so polni
        time.sleep(0.1)
        self.prisotnostKolo = self.client.db_read(1, 6, 2)
        #(self.prisotnostKolo)
        k = 0
        for i in range(2):
            x = 1
            for j in range(8):
                if self.prisotnostKolo[i] & x != 0:
                    self.kolesa[k] = 1
                else:
                    self.kolesa[k] = 0
                k += 1
                x *= 2
        #print(self.kolesa)

    def sposodiScreen(self):                                            # st tipk odvisno od prisotnosti koles
        self.prisotnostKolesa()
        self.zeroBikes.hide()
        try:
            (len(self.kolesa) - self.kolesa[::-1].index(1))             # zadnji indeks enke v database tabeli
        except:                                                         # če ni nobenega kolesa(v bytearrayu ni 1)
            self.zeroBikes.show()                                       # izvedi except
            print('There are no bikes available')
        for i in range(16):                                             # prikaži samo tiste tipke, katerih kolesa
            self.btn_vrni[i].hide()
            if self.kolesa[i] == 0:                                     # so parkirana
                self.btn[i].hide()
            elif self.kolesa[i] == 1:
                self.btn[i].show()

        self.stackedWidget.setCurrentIndex(1)

    def vrniScreen(self):
        self.prisotnostKolesa()
        self.zeroBikes.hide()
        for i in range(16):
            self.btn[i].hide()
            if self.kolesa[i] == 1 or (i > self.stStebrickov[1]-1 and self.kolesa[i] == 0):
                self.btn_vrni[i].hide()
            elif self.kolesa[i] == 0:
                self.btn_vrni[i].show()

        self.stackedWidget.setCurrentIndex(1)
    def aktivniKolesarji(self):
        pass

    def ponastavitevTabel(self):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec_())
