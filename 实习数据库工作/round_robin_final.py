# -*- coding: utf-8 -*-
import os
import chardet
import xlwt
import xlrd
import xdrlib, sys
#import PyMysql
import MySQLdb
import types
import csv
import math


def open_file(file = 'test.xlsx'):
    try:
        data = xlrd.open_workbook(file)
        return data
    except Exception, e:
        print str(e)

def testXlwt(file = 'new.xls', list = []):
    book = xlwt.Workbook()
    sheet1 = book.add_sheet('hello')
    i = 0
    for app in list:
        j = 0
        for x in app:
            sheet1.write(i, j, x)
            j = j + 1
        i = i + 1

    book.save(file)

def excel_table_byindex(file = 'test.xlsx', colnameindex = 0, by_index = 0):
    data = open_file(file)
    table = data.sheets()[by_index]
    nrows = table.nrows
    ncols = table.ncols
    colnames = table.row_values(colnameindex)
    list = []
    for rownum in range(0, nrows):
        row = table.row_values(rownum)
        if row:
            app = []
            for i in range(len(colnames)):
                app.append(row[i])
            list.append(app)

    testXlwt('new.xls', list)
    return list

def main():
    tables = excel_table_byindex("/Users/Den1er/Documents/Caict/数据集/样机列表.xlsx", 0, 0)
    #print tables
    conn = MySQLdb.connect("10.2.47.147", "root", "123", "testproject")
    cursor = conn.cursor()
    exclude = 1
    for row in tables:
        a = """INSERT INTO cellphone(cellphone_id, model, brand, price, model_exp,
                cell_source, IMEI, software_edition, test_content, pixel_count_V,
                pixel_count_H, pixel_count_MPix, Aspect_Ratio, DXOMark_Photo, Test_Mode)
                VALUES("""
        if exclude == 1:
            exclude = 0
            continue
        for data in row:
            if data == '':
                data = 'null'

            if isinstance(data, basestring) and data != 'null':
                data = '"' + data + '"'

            if type(data) == type(1.0):
                data = int(data)
                data = repr(data)

            a += data + ','

        a = a[: -1]
        a += ')'
        #print a
        try:
            cursor.execute(a)
            conn.commit()
        except:
            conn.rollback()
    conn.close()


def scanfile(path):
    files = os.listdir(path)
    s = []
    for file in files:
        if not os.path.isdir(file):
            #print os.path.basename(file)
            s.append(os.path.basename(file))

    return s

def filenamesplit(filenamelist):
    splitedlist = []
    for filename in filenamelist:
        #print filename
        splitedlist.append(filename.split('_'))
    return splitedlist

def dealWithForeignKey(inf, conn, rootpath):
    cursor = conn.cursor()

    #先插入光源的表
    light_query = """INSERT INTO light_source(light_source_id, device_type, light_source_type, lux)
            VALUES ("""
    light_source_id = '"' + inf[3] + "_" + inf[4] + "_" + inf[5] + '"'
    device_type = '"' + inf[3] + '"'
    light_source_type = '"' + inf[4] + '"'
    lux = '"' + inf[5] + '"'
    light_query = light_query + light_source_id + ' ,' + device_type + ' ,' + light_source_type + ' ,' + lux + ')'
    #print light_query
    try:
        cursor.execute(light_query)
        conn.commit()
    except:
        conn.rollback()
    #要执行插入操作,需要拿到光源id,图卡id,手机id,以及metric编号
    #查询手机信息
    cellphone_query = """SELECT cellphone_id FROM cellphone
                        WHERE model = '%s' AND brand = '%s'""" % (inf[1], inf[0])
    #print cellphone_query
    try:
        cursor.execute(cellphone_query)
        cellphone_id = cursor.fetchone()[0]
        #print cellphone_id
    except:
        conn.rollback()
    return light_source_id, cellphone_id, cursor

def doeSFR2or4(inf, conn, rootpath):
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    #print "light_source:%s, cellphone_id:%d"%(light_source_id, cellphone_id)
    #查询图卡与计算项信息
    cardAndetric_query = """SELECT physical_id, metric FROM round_robin_card_metric_pair
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    OM = 0
    Ori_OM = 0
    QL = 0
    Ori_QL = 0
    cursor.execute(cardAndetric_query)
    card_metric_set = cursor.fetchall()
    #print card_metric_set
    for card_metric_id in card_metric_set:
        #print card_metric_id[0], card_metric_id[1]
        if card_metric_id[1] == "Acutance":
            try:
                #print "do actance"
                OM = 0
                QL = 0
                Ori_QL = 0
                Ori_OM = 0
                resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_Y_multi.csv"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                #print respath
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Acutance)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                #print graphpath
                respath = rootpath + "/Results/" + resfilename
                #print respath

                with open(respath, 'rb') as csvfile:
                    tables = csv.reader(csvfile)
                    rows = [row for row in tables]
                #print rows
                #print len(rows)
                for index in range(len(rows)):
                    #print rows[index]
                    if len(rows[index]) == 0:
                        continue
                    if rows[index][0] == 'Computer Monitor Acutance':
                        OM = rows[index][1]
                        Ori_OM = OM
                    elif rows[index][0] == 'Computer Monitor Quality Loss':
                        QL = rows[index][1]
                        Ori_QL = QL
                #print "lab:%s"%(lab)
                #print "OM:%s"%(OM)
                lab = (rootpath.split("/"))[-1]
                distance = inf[6]
                #插入信息
                round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                #print round_robin_insert
                cursor.execute(round_robin_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_id[1] == "Visual noise":
            try:
                #print "do visual noise"
                OM = 0
                QL = 0
                Ori_QL = 0
                Ori_OM = 0
                resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_Y_multi.csv"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                #print respath
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Visual Noise)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                #print graphpath
                respath = rootpath + "/Results/" + resfilename
                #print respath

                with open(respath, 'rb') as csvfile:
                    tables = csv.reader(csvfile)
                    rows = [row for row in tables]
                for index in range(len(rows)):
                    #print rows[index]
                    if len(rows[index]) == 0:
                        continue
                    if rows[index][0] == 'CPIQ Visual Noise 1 @ L*=50':
                        OM = rows[index][1]
                        Ori_OM = OM
                    elif rows[index][0] == 'Quality Loss QL (CPIQ Visual Noise 1 @ L*=50)':
                        QL = rows[index][1]
                        Ori_QL = QL
                #print "lab:%s"%(lab)
                #print "OM:%s"%(OM)
                lab = (rootpath.split("/"))[-1]
                distance = inf[6]
                #插入信息
                round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                #print round_robin_insert
                cursor.execute(round_robin_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
        else:
            print "others"



def dogrey(inf, conn, rootpath):
    #print inf
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric FROM round_robin_card_metric_pair
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    try:
        cursor.execute(cardAndetric_query)
        card_metric_set = cursor.fetchall()
        #print card_metric_set
        for card_metric_id in card_metric_set:
            #print "do grey"
            OM = 0
            QL = 0
            Ori_QL = 0
            Ori_OM = 0
            resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_LF_Y.csv"""\
                      %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
            #print respath
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s"""\
                      %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            #print graphpath
            respath = rootpath + "/Results/" + resfilename
            #print respath

            with open(respath, 'rb') as csvfile:
                tables = csv.reader(csvfile)
                rows = [row for row in tables]
            #print rows
            #print len(rows)
            for index in range(len(rows)):
                #print rows[index]
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == 'Dc CPIQ max color nonuniformity':
                    OM = rows[index][1]
                    Ori_OM = OM
                elif rows[index][0] == 'QL CPIQ quality loss':
                    QL = rows[index][1]
                    Ori_QL = QL
            #print "lab:%s"%(lab)
            #print "OM:%s"%(OM)
            lab = (rootpath.split("/"))[-1]
            distance = inf[6]
            #插入信息
            round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                    VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
            """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
            #print round_robin_insert
            cursor.execute(round_robin_insert)
            conn.commit()
    except Exception, e:
        print 'repr(e):\t', repr(e)
        conn.rollback()

def doImBW(inf, conn, rootpath):
    #print inf
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric FROM round_robin_card_metric_pair
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    try:
        cursor.execute(cardAndetric_query)
        card_metric_set = cursor.fetchall()
        #print card_metric_set
        for card_metric_id in card_metric_set:
            #print "do ImBW"
            OM = 0
            QL = 0
            Ori_QL = 0
            Ori_OM = 0
            resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_Y_Random.csv"""\
                      %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
            #print respath
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s"""\
                      %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            #print graphpath
            respath = rootpath + "/Results/" + resfilename
            #print respath

            with open(respath, 'rb') as csvfile:
                tables = csv.reader(csvfile)
                rows = [row for row in tables]
            #print rows
            #print len(rows)
            for index in range(len(rows)):
                #print rows[index]
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == 'Computer Monitor Acutance':
                    OM = rows[index][1]
                    Ori_OM = OM
                elif rows[index][0] == 'Computer Monitor Quality Loss':
                    QL = rows[index][1]
                    Ori_QL = QL
            #print "lab:%s"%(lab)
            #print "OM:%s"%(OM)
            lab = (rootpath.split("/"))[-1]
            distance = inf[6]
            #插入信息
            round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                    VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
            """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
            #print round_robin_insert
            cursor.execute(round_robin_insert)
            conn.commit()
    except Exception, e:
        print 'repr(e):\t', repr(e)
        conn.rollback()

def doImDot(inf, conn, rootpath):
    #print inf
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    #print "light_source:%s, cellphone_id:%d"%(light_source_id, cellphone_id)
    #查询图卡与计算项信息
    cardAndetric_query = """SELECT physical_id, metric FROM round_robin_card_metric_pair
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    OM = 0
    Ori_OM = 0
    QL = 0
    Ori_QL = 0
    cursor.execute(cardAndetric_query)
    card_metric_set = cursor.fetchall()
    #print card_metric_set
    for card_metric_id in card_metric_set:
            #print card_metric_id[0], card_metric_id[1]
            if card_metric_id[1] == "Lateral Chromatic Aberration(%)":
                try:
                    #print "do actance"
                    OM = 0
                    QL = 0
                    Ori_QL = 0
                    Ori_OM = 0
                    resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_summary.csv"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                    #print respath
                    graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Lateral Chromatic Aberration)"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                    #print graphpath
                    respath = rootpath + "/Results/" + resfilename
                    #print respath

                    with open(respath, 'rb') as csvfile:
                        tables = csv.reader(csvfile)
                        rows = [row for row in tables]
                    #print rows
                    #print len(rows)
                    for index in range(len(rows)):
                        #print rows[index]
                        if len(rows[index]) == 0:
                            continue
                        if rows[index][0] == 'Maximum LAC CPIQ Metric':
                            OM = rows[index][1]
                            Ori_OM = OM
                        elif rows[index][0] == 'CPIQ Quality Loss':
                            QL = rows[index][1]
                            Ori_QL = QL
                    #print "lab:%s"%(lab)
                    #print "OM:%s"%(OM)
                    lab = (rootpath.split("/"))[-1]
                    distance = inf[6]
                    #插入信息
                    round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                            VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                    #print round_robin_insert
                    cursor.execute(round_robin_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()
            elif card_metric_id[1] == "Local geometric distortion(%)":
                #print "do visual noise"
                try:
                    OM = 0
                    QL = 0
                    Ori_QL = 0
                    Ori_OM = 0
                    resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_summary.csv"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                    #print respath
                    graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Local geometric distortion)"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                    #print graphpath
                    respath = rootpath + "/Results/" + resfilename
                    #print respath

                    with open(respath, 'rb') as csvfile:
                        tables = csv.reader(csvfile)
                        rows = [row for row in tables]
                    for index in range(len(rows)):
                        #print rows[index]
                        if len(rows[index]) == 0:
                            continue
                        if rows[index][0] == 'CPIQ Distortion Metric (as a %)':
                            OM = rows[index][1]
                            Ori_OM = OM
                        elif rows[index][0] == 'CPIQ Quality Loss':
                            QL = rows[index][1]
                            Ori_QL = QL
                    #print "lab:%s"%(lab)
                    #print "OM:%s"%(OM)
                    lab = (rootpath.split("/"))[-1]
                    distance = inf[6]
                    #插入信息
                    round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                            VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                    #print round_robin_insert
                    cursor.execute(round_robin_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()
            else:
                print "others"

def doSG(inf, conn, rootpath):
    #print inf
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    #print "light_source:%s, cellphone_id:%d"%(light_source_id, cellphone_id)
    #查询图卡与计算项信息
    cardAndetric_query = """SELECT physical_id, metric FROM round_robin_card_metric_pair
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    OM = 0
    Ori_OM = 0
    QL = 0
    Ori_QL = 0
    cursor.execute(cardAndetric_query)
    card_metric_set = cursor.fetchall()
    #print card_metric_set
    for card_metric_id in card_metric_set:
            #print card_metric_id[0], card_metric_id[1]
            if card_metric_id[1] == "Chromal level(%)":
                try:
                    #print "do actance"
                    OM = 0
                    QL = 0
                    Ori_QL = 0
                    Ori_OM = 0
                    resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_jpg_multicharts.csv"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                    #print respath
                    graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Chromal level)"""\
                              %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                    #print graphpath
                    respath = rootpath + "/Results/" + resfilename
                    # respath

                    with open(respath, 'rb') as csvfile:
                        tables = csv.reader(csvfile)
                        rows = [row for row in tables]
                    #print rows
                    #print len(rows)
                    for index in range(len(rows)):
                        #print rows[index]
                        if len(rows[index]) == 0:
                            continue
                        if rows[index][0] == 'Mean chroma level CPIQ %':
                            OM = rows[index][1]
                            Ori_OM = OM
                        elif rows[index][0] == 'CPIQ Chroma quality loss':
                            QL = rows[index][1]
                            Ori_QL = QL
                    #print "lab:%s"%(lab)
                    #print "OM:%s"%(OM)
                    lab = (rootpath.split("/"))[-1]
                    distance = inf[6]
                    #插入信息
                    round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                            VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                    #print round_robin_insert
                    cursor.execute(round_robin_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()
            elif card_metric_id[1] == "AE":
                try:
                    #print "do visual noise"
                    OM = 0
                    QL = 0
                    Ori_QL = 0
                    Ori_OM = 0
                    resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_jpg_multicharts.csv"""\
                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
                    #print respath
                    graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(AE)"""\
                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                    #print graphpath
                    respath = rootpath + "/Results/" + resfilename
                    #print respath

                    with open(respath, 'rb') as csvfile:
                        tables = csv.reader(csvfile)
                        rows = [row for row in tables]
                    count = 0
                    #print rows
                    for index in range(len(rows)):
                        #print rows[index]
                        if len(rows[index]) == 0:
                            continue
                        if rows[index][0] == ' 64':
                            #print rows[index]
                            OM = rows[index][5].split(' ')[1]
                            Ori_OM = OM
                            break
                    a = 0.537
                    b = 0.416
                    c = 1.739
                    d = 250
                    QL = d * (1 - math.exp(-pow(b * abs(float(OM) - a), c)))
                    #print "lab:%s"%(lab)

                    #print "OM:%s"%(OM)
                    lab = (rootpath.split("/"))[-1]
                    distance = inf[6]
                    #插入信息
                    round_robin_insert = """INSERT INTO round_robin(graph_path, cellphone_id, light_source_id, card_metric_id, lab, distance, OM, QL, Ori_OM, Ori_QL)
                                          VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f)
                  """%(graphpath, cellphone_id, light_source_id, int(card_metric_id[0]), lab, distance, float(OM), float(QL), float(Ori_OM), float(Ori_QL))
                    #print round_robin_insert
                    cursor.execute(round_robin_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()
                else:
                    print "others"


def doDefault(inf):
    print "default function"

def classify(list, conn, rootpath):
    card = list[2]
    if card == 'eSFR2':
        doeSFR2or4(list, conn, rootpath)
    elif card == 'eSFR4':
        doeSFR2or4(list, conn, rootpath)
    elif card == 'grey':
        dogrey(list, conn, rootpath)
    elif card == 'Im B&W Coins':
        doImBW(list, conn, rootpath)
    elif card == 'Im Dot':
        doImDot(list, conn, rootpath)
    elif card == 'SG':
        doSG(list, conn, rootpath)
    else:
        doDefault(list)

def controller(file, rootpath):
    conn = MySQLdb.connect("10.2.47.147", "root", "123", "testproject")
    for slice in file:
        if len(slice) > 2:
            classify(slice, conn, rootpath)

    conn.close()

def scanFromRoot(rootpath):
    files = os.listdir(rootpath)
    for file in files:
        if os.path.isdir(rootpath + '/' + os.path.basename(file)):
            path = rootpath + '/' + os.path.basename(file)
            filenamelist = scanfile(path)
            res = filenamesplit(filenamelist)
            controller(res, path)


if __name__ == "__main__":
    #main()
    rootpath = "/Users/Den1er/Documents/Caict/数据集/5_CPIQ round-robin/CTTL"
    scanFromRoot(rootpath)
    print os.path.isdir("/Users/Den1er/Documents/Caict/数据集/5_CPIQ round-robin/CTTL/7002")
    '''
    fileread = open("/Users/Den1er/Documents/Caict/数据集/样机列表.xlsx", 'rb')
    fdata = fileread.readline()
    enc = chardet.detect(fdata)
    print enc
    fileread.close()
    '''
    '''
    rootpath = "/Users/Den1er/Documents/Caict/数据集/5_CPIQ round-robin/CTTL/7002"
    filenamelist = scanfile("/Users/Den1er/Documents/Caict/数据集/5_CPIQ round-robin/CTTL/7002")
    print filenamelist
    res = filenamesplit(filenamelist)
    print res

    controller(res, rootpath)
    '''
    '''
    conn = MySQLdb.connect("10.2.47.147", "root", "123", "testproject")
    cursor = conn.cursor()
    cursor.execute("show tables;")
    data = cursor.fetchall()
    print data
    '''