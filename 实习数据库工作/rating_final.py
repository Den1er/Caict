# -*- coding: utf-8 -*-
import os
import chardet
import xlwt
import xlrd
import xdrlib, sys
import MySQLdb
import types
import csv
import math
import re

def open_file(file = 'test.xlsx'):
    try:
        data = xlrd.open_workbook(file)
        return data
    except Exception, e:
        print str(e)

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

    #testXlwt('new.xls', list)
    return list

def open_txt(file):
    lines = []
    list = []
    with open(file, 'r') as f:
        lines = f.readlines()
    for row in lines:
        list.append(row.split('\t'))
    return list

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


def handleDxO(inf, conn, rootpath):
    #print "DxO"
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric, value FROM card_metric_value_group
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    cursor.execute(cardAndetric_query)
    card_metric_value_set = cursor.fetchall()
    #print card_metric_set
    #print rootpath
    #print inf
    #print card_metric_value_set
    for card_metric_value_id in card_metric_value_set:
        if inf[2] == 'DxO SFR':
            #print 'DxO'
            CPIQ = 0
            respath = rootpath + "/Results"
            #对目录下的所有文件遍历,进行正则匹配,找到目标xls文件
            matchedfilename = "RADMTF_%s_%s_%s_%s_%s_%s"%(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5])
            #print matchedfilename
            files = os.listdir(respath)
            for file in files:
                if re.match(matchedfilename, os.path.basename(file)):
                    #print os.path.basename(file)
                    rows = excel_table_byindex(respath + '/' + os.path.basename(file))
                    #print rows

                    for row in rows:
                        if row[1] == 'CPIQ Sharpness':
                            CPIQ = row[3]
                            #print CPIQ
                            break
            try:
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                lab = (rootpath.split("/"))[-1]
                distance = inf[6]
                rating_insert = """INSERT INTO rating_single(lab, graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, CPIQ, Ori_CPIQ)
                                      VALUES ("%s", "%s", %d, %s, %d, "%s", %f, %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(CPIQ), float(CPIQ))
                #print rating_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif inf[2] == 'DxO Dot':
            #print "DxO Dot"
            CPIQ = 0
            respath = rootpath + "/Results"
            #对目录下的所有文件遍历,进行正则匹配,找到目标xls文件
            matchedfilename = "DC_%s_%s_%s_%s_%s_%s"%(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5])
            #print matchedfilename
            files = os.listdir(respath)
            for file in files:
                if re.match(matchedfilename, os.path.basename(file)):
                    #print os.path.basename(file)
                    rows = excel_table_byindex(respath + '/' + os.path.basename(file))
                    #print rows
                    if card_metric_value_id[2] == 'MAX in pixels':
                        for index in range(len(rows)):
                            if rows[index][3] == 'in pixels':
                                CPIQ = rows[index + 1][3]
                                #print CPIQ
                                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Max in pixels)"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                break
                    elif card_metric_value_id[2] == 'MAX/1000':
                        for index in range(len(rows)):
                            if rows[index][3] == 'in pixels':
                                CPIQ = rows[index + 1][5]
                                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MAX/1000)"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                #print CPIQ
                                break
                    elif card_metric_value_id[2] == 'MAX in μm(20*30 cm eq.)':
                        for index in range(len(rows)):
                            if rows[index][3] == 'in pixels':
                                CPIQ = rows[index + 1][7]
                                #print CPIQ
                                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MAX in μm(20*30 cm eq.))"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                break
                    elif card_metric_value_id[2] == 'TV distortion':
                        for index in range(len(rows)):
                            if rows[index][1] == 'TV distortion':
                                CPIQ = rows[index][7]
                                #print CPIQ
                                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(TV distortion)"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                break
            try:

                lab = (rootpath.split("/"))[-1]
                distance = inf[6]
                rating_insert = """INSERT INTO rating_single(lab, graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, CPIQ, Ori_CPIQ)
                                      VALUES ("%s", "%s", %d, %s, %d, "%s", %f, %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(CPIQ), float(CPIQ))
                #print rating_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif inf[2] == 'DxO texture':
            #print "DxO texture"
            CPIQ = 0
            respath = rootpath + "/Results"
            #对目录下的所有文件遍历,进行正则匹配,找到目标xls文件
            matchedfilename = "TEX_%s_%s_%s_%s_%s_%s"%(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5])
            #print matchedfilename
            files = os.listdir(respath)
            for file in files:
                if re.match(matchedfilename, os.path.basename(file)):
                    #print os.path.basename(file)
                    rows = excel_table_byindex(respath + '/' + os.path.basename(file))
                    #print rows
                    if card_metric_value_id[2] == 'Professional Photo Print(closer)锐度':
                        count = 0
                        for index in range(len(rows)):
                            if rows[index][1] == 'Luminance Channel':
                                count = count + 1
                                if count == 3:
                                    CPIQ = rows[index][3]
                                    graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(Professional Photo Print(closer)锐度)"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                    break
                    elif card_metric_value_id[2] == 'computer display锐度':
                        for index in range(len(rows)):
                            if rows[index][1] == 'Computer Display':
                                CPIQ = rows[index][5]
                                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(computer display锐度)"""\
                                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                                break

            try:

                lab = (rootpath.split("/"))[-1]
                distance = inf[6]
                rating_insert = """INSERT INTO rating_single(lab, graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, CPIQ, Ori_CPIQ)
                                      VALUES ("%s", "%s", %d, %s, %d, "%s", %f, %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(CPIQ), float(CPIQ))
                #print rating_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()


def handleTE255orgrey(inf, conn, rootpath):
    print "TE255orgrey"

    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric, value FROM card_metric_value_group
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    cursor.execute(cardAndetric_query)
    card_metric_value_set = cursor.fetchall()
    for card_metric_value_id in card_metric_value_set:
        if card_metric_value_id[2] == 'KA、KB、KC、KD均值':
            resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_LF_Y.csv"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(KA、KB、KC、KD均值)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            respath = rootpath + "/Results/" + resfilename

            Y_Center = 0
            Y_UL = 0
            Y_LL = 0
            Y_UR = 0
            Y_LR = 0
            with open(respath, 'rb') as csvfile:
                    tables = csv.reader(csvfile)
                    rows = [row for row in tables]
            #print rows
            for index in range(len(rows)):
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == 'Y (Luminance)':
                    Y_Center = rows[index][1]
                    Y_UL = rows[index][2]
                    Y_LL = rows[index][3]
                    Y_UR = rows[index][4]
                    Y_LR = rows[index][5]
                    break
            CPIQ = (float(Y_Center) + float(Y_UL) + float(Y_LL) + float(Y_UR) + float(Y_LR)) / 5
            lab = (rootpath.split("/"))[-1]
            distance = inf[6]
            rating_insert = """INSERT INTO rating_single_5(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, Y_Center, Y_UL, Y_LL, Y_UR, Y_LR)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, CPIQ, float(Y_Center), float(Y_UL), float(Y_LL), float(Y_UR), float(Y_LR))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
        elif card_metric_value_id[1] == 'Color uniformity':
            #print "Color uniformity"
            resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_LF_Y.csv"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])

            respath = rootpath + "/Results/" + resfilename
            R_B_Center = R_B_UL = R_B_LL = R_B_UR = R_B_LR = R_B_L_Ctr = R_B_R_Ctr = R_B_T_Ctr =  R_B_B_Ctr = 0
            R_G_Center = R_G_UL = R_G_LL = R_G_UR = R_G_LR = R_G_L_Ctr = R_G_R_Ctr = R_G_T_Ctr =  R_G_B_Ctr = 0
            B_G_Center = B_G_UL = B_G_LL = B_G_UR = B_G_LR = B_G_L_Ctr = B_G_R_Ctr = B_G_T_Ctr =  B_G_B_Ctr = 0
            list = []
            with open(respath, 'rb') as csvfile:
                    tables = csv.reader(csvfile)
                    rows = [row for row in tables]
            for index in range(len(rows)):
                if len(rows[index]) == 0:
                        continue
                if rows[index][0] == 'R/B normlzd':
                    R_B_Center = float(rows[index][1])
                    list.append(R_B_Center)
                    R_B_UL = float(rows[index][2])
                    list.append(R_B_UL)
                    R_B_LL = float(rows[index][3])
                    list.append(R_B_LL)
                    R_B_UR = float(rows[index][4])
                    list.append(R_B_UR)
                    R_B_LR = float(rows[index][5])
                    list.append(R_B_LR)
                    R_B_L_Ctr = float(rows[index][6])
                    list.append(R_B_L_Ctr)
                    R_B_R_Ctr = float(rows[index][7])
                    list.append(R_B_R_Ctr)
                    R_B_T_Ctr = float(rows[index][8])
                    list.append(R_B_T_Ctr)
                    R_B_B_Ctr = float(rows[index][9])
                    list.append(R_B_B_Ctr)
                    R_G_Center = float(rows[index + 1][1])
                    list.append(R_G_Center)
                    R_G_UL = float(rows[index + 1][2])
                    list.append(R_G_UL)
                    R_G_LL = float(rows[index + 1][3])
                    list.append(R_G_LL)
                    R_G_UR = float(rows[index + 1][4])
                    list.append(R_G_UR)
                    R_G_LR = float(rows[index + 1][5])
                    list.append(R_G_LR)
                    R_G_L_Ctr = float(rows[index + 1][6])
                    list.append(R_G_L_Ctr)
                    R_G_R_Ctr = float(rows[index + 1][7])
                    list.append(R_G_R_Ctr)
                    R_G_T_Ctr = float(rows[index + 1][8])
                    list.append(R_G_T_Ctr)
                    R_G_B_Ctr = float(rows[index + 1][9])
                    list.append(R_G_B_Ctr)
                    B_G_Center = float(rows[index + 2][1])
                    list.append(R_G_Center)
                    B_G_UL = float(rows[index + 2][2])
                    list.append(R_G_UL)
                    B_G_LL = float(rows[index + 2][3])
                    list.append(R_G_LL)
                    B_G_UR = float(rows[index + 2][4])
                    list.append(R_G_UR)
                    B_G_LR = float(rows[index + 2][5])
                    list.append(R_G_LR)
                    B_G_L_Ctr = float(rows[index + 2][6])
                    list.append(R_G_L_Ctr)
                    B_G_R_Ctr = float(rows[index + 2][7])
                    list.append(R_G_R_Ctr)
                    B_G_T_Ctr = float(rows[index + 2][8])
                    list.append(R_G_T_Ctr)
                    B_G_B_Ctr = float(rows[index + 2][9])
                    list.append(R_G_B_Ctr)
                    break

            lab = (rootpath.split("/"))[-1]
            distance = inf[6]
            minofList = min(list)
            maxofList = max(list)
            sumofList = 0
            for item in list:
                sumofList += float(item)
            meanofList = sumofList / len(list)
            maxDistanceFromOne = 0
            if abs(minofList - 1) > abs(maxofList - 1):
                maxDistanceFromOne = abs(minofList - 1)
            else:
                maxDistanceFromOne = abs(maxofList - 1)
            if card_metric_value_id[2] == '九点R/B R/G B/G MIN':
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(九点R/B R/G B/G MIN)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                rating_insert = """INSERT INTO rating_single_27(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, R_B_normlzd_Center, R_B_normlzd_UL, R_B_normlzd_LL, R_B_normlzd_UR, R_B_normlzd_LR, R_B_normlzd_L_Ctr, R_B_normlzd_R_Ctr, R_B_normlzd_T_Ctr, R_B_normlzd_B_Ctr, R_G_normlzd_Center, R_G_normlzd_UL, R_G_normlzd_LL, R_G_normlzd_UR, R_G_normlzd_LR, R_G_normlzd_L_Ctr, R_G_normlzd_R_Ctr, R_G_normlzd_T_Ctr, R_G_normlzd_B_Ctr, B_G_normlzd_UL, B_G_normlzd_LL, B_G_normlzd_UR, B_G_normlzd_LR, B_G_normlzd_L_Ctr, B_G_normlzd_R_Ctr, B_G_normlzd_T_Ctr, B_G_normlzd_B_Ctr, B_G_normlzd_Center)
                                          VALUES ("%s", %d, %s, %d, "%s", "%s", %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, minofList,\
                         float(R_B_Center), float(R_B_UL), float(R_B_LL), float(R_B_UR), float(R_B_LR), float(R_B_L_Ctr), float(R_B_R_Ctr), float(R_B_T_Ctr), float(R_B_B_Ctr), \
                         float(R_G_Center), float(R_G_UL), float(R_G_LL), float(R_G_UR), float(R_G_LR), float(R_G_L_Ctr), float(R_G_R_Ctr), float(R_G_T_Ctr), float(R_G_B_Ctr), \
                         float(B_G_Center), float(B_G_UL), float(B_G_LL), float(B_G_UR), float(B_G_LR), float(B_G_L_Ctr), float(B_G_R_Ctr), float(B_G_T_Ctr), float(B_G_B_Ctr))
                #print rating_insert
                try:
                    #print round_robin_insert
                    cursor.execute(rating_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()

            elif card_metric_value_id[2] == '九点R/B R/G B/G 平均值':
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(九点R/B R/G B/G 平均值)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                rating_insert = """INSERT INTO rating_single_27(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, R_B_normlzd_Center, R_B_normlzd_UL, R_B_normlzd_LL, R_B_normlzd_UR, R_B_normlzd_LR, R_B_normlzd_L_Ctr, R_B_normlzd_R_Ctr, R_B_normlzd_T_Ctr, R_B_normlzd_B_Ctr, R_G_normlzd_Center, R_G_normlzd_UL, R_G_normlzd_LL, R_G_normlzd_UR, R_G_normlzd_LR, R_G_normlzd_L_Ctr, R_G_normlzd_R_Ctr, R_G_normlzd_T_Ctr, R_G_normlzd_B_Ctr, B_G_normlzd_UL, B_G_normlzd_LL, B_G_normlzd_UR, B_G_normlzd_LR, B_G_normlzd_L_Ctr, B_G_normlzd_R_Ctr, B_G_normlzd_T_Ctr, B_G_normlzd_B_Ctr, B_G_normlzd_Center)
                                          VALUES ("%s", %d, %s, %d, "%s", "%s", %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, meanofList,\
                         float(R_B_Center), float(R_B_UL), float(R_B_LL), float(R_B_UR), float(R_B_LR), float(R_B_L_Ctr), float(R_B_R_Ctr), float(R_B_T_Ctr), float(R_B_B_Ctr), \
                         float(R_G_Center), float(R_G_UL), float(R_G_LL), float(R_G_UR), float(R_G_LR), float(R_G_L_Ctr), float(R_G_R_Ctr), float(R_G_T_Ctr), float(R_G_B_Ctr), \
                         float(B_G_Center), float(B_G_UL), float(B_G_LL), float(B_G_UR), float(B_G_LR), float(B_G_L_Ctr), float(B_G_R_Ctr), float(B_G_T_Ctr), float(B_G_B_Ctr))
                try:
                    #print round_robin_insert
                    cursor.execute(rating_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()

            elif card_metric_value_id[2] == '九点R/B R/G B/G MAX':
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(九点R/B R/G B/G MAX)""" \
                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                rating_insert = """INSERT INTO rating_single_27(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, R_B_normlzd_Center, R_B_normlzd_UL, R_B_normlzd_LL, R_B_normlzd_UR, R_B_normlzd_LR, R_B_normlzd_L_Ctr, R_B_normlzd_R_Ctr, R_B_normlzd_T_Ctr, R_B_normlzd_B_Ctr, R_G_normlzd_Center, R_G_normlzd_UL, R_G_normlzd_LL, R_G_normlzd_UR, R_G_normlzd_LR, R_G_normlzd_L_Ctr, R_G_normlzd_R_Ctr, R_G_normlzd_T_Ctr, R_G_normlzd_B_Ctr, B_G_normlzd_UL, B_G_normlzd_LL, B_G_normlzd_UR, B_G_normlzd_LR, B_G_normlzd_L_Ctr, B_G_normlzd_R_Ctr, B_G_normlzd_T_Ctr, B_G_normlzd_B_Ctr, B_G_normlzd_Center)
                                          VALUES ("%s", %d, %s, %d, "%s", "%s", %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, maxofList,\
                         float(R_B_Center), float(R_B_UL), float(R_B_LL), float(R_B_UR), float(R_B_LR), float(R_B_L_Ctr), float(R_B_R_Ctr), float(R_B_T_Ctr), float(R_B_B_Ctr), \
                         float(R_G_Center), float(R_G_UL), float(R_G_LL), float(R_G_UR), float(R_G_LR), float(R_G_L_Ctr), float(R_G_R_Ctr), float(R_G_T_Ctr), float(R_G_B_Ctr), \
                         float(B_G_Center), float(B_G_UL), float(B_G_LL), float(B_G_UR), float(B_G_LR), float(B_G_L_Ctr), float(B_G_R_Ctr), float(B_G_T_Ctr), float(B_G_B_Ctr))
                #print rating_insert
                try:
                    #print round_robin_insert
                    cursor.execute(rating_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()

            elif card_metric_value_id[2] == '九点R/B R/G B/G 与1差值的绝对值的最大值':
                graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(九点R/B R/G B/G 与1差值的绝对值的最大值)""" \
                            %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
                rating_insert = """INSERT INTO rating_single_27(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, R_B_normlzd_Center, R_B_normlzd_UL, R_B_normlzd_LL, R_B_normlzd_UR, R_B_normlzd_LR, R_B_normlzd_L_Ctr, R_B_normlzd_R_Ctr, R_B_normlzd_T_Ctr, R_B_normlzd_B_Ctr, R_G_normlzd_Center, R_G_normlzd_UL, R_G_normlzd_LL, R_G_normlzd_UR, R_G_normlzd_LR, R_G_normlzd_L_Ctr, R_G_normlzd_R_Ctr, R_G_normlzd_T_Ctr, R_G_normlzd_B_Ctr, B_G_normlzd_UL, B_G_normlzd_LL, B_G_normlzd_UR, B_G_normlzd_LR, B_G_normlzd_L_Ctr, B_G_normlzd_R_Ctr, B_G_normlzd_T_Ctr, B_G_normlzd_B_Ctr, B_G_normlzd_Center)
                                          VALUES ("%s", %d, %s, %d, "%s", "%s", %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f,
                                                  %f, %f, %f, %f, %f, %f, %f, %f, %f)
                    """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, maxDistanceFromOne,\
                         float(R_B_Center), float(R_B_UL), float(R_B_LL), float(R_B_UR), float(R_B_LR), float(R_B_L_Ctr), float(R_B_R_Ctr), float(R_B_T_Ctr), float(R_B_B_Ctr), \
                         float(R_G_Center), float(R_G_UL), float(R_G_LL), float(R_G_UR), float(R_G_LR), float(R_G_L_Ctr), float(R_G_R_Ctr), float(R_G_T_Ctr), float(R_G_B_Ctr), \
                         float(B_G_Center), float(B_G_UL), float(B_G_LL), float(B_G_UR), float(B_G_LR), float(B_G_L_Ctr), float(B_G_R_Ctr), float(B_G_T_Ctr), float(B_G_B_Ctr))
                #print rating_insert
                try:
                    #print round_robin_insert
                    cursor.execute(rating_insert)
                    conn.commit()
                except Exception, e:
                    print 'repr(e):\t', repr(e)
                    conn.rollback()

def handleClolorchecker(inf, conn, rootpath):
    print "handleClolor"
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric, value FROM card_metric_value_group
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    cursor.execute(cardAndetric_query)
    card_metric_value_set = cursor.fetchall()
    for card_metric_value_id in card_metric_value_set:
        resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_summary.csv"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])

        respath = rootpath + "/Results/" + resfilename
        lab = (rootpath.split("/"))[-1]
        distance = inf[6]
        with open(respath, 'rb') as csvfile:
            tables = csv.reader(csvfile)
            rows = [row for row in tables]
        if card_metric_value_id[2] == '各色块对应的饱和度S值的最大值':
            WB_ERR_S_20 = WB_ERR_S_21 = WB_ERR_S_22 = WB_ERR_S_23 = 0
            list4 = []
            for index in range(len(rows)):
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == '20':
                    WB_ERR_S_20 = rows[index][9]
                    WB_ERR_S_21 = rows[index + 1][9]
                    WB_ERR_S_22 = rows[index + 2][9]
                    WB_ERR_S_23 = rows[index + 3][9]
                    list4.append(float(WB_ERR_S_20))
                    list4.append(float(WB_ERR_S_21))
                    list4.append(float(WB_ERR_S_22))
                    list4.append(float(WB_ERR_S_23))
                    break
            maxofList4 = max(list4)
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(各色块对应的饱和度S值的最大值)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_4(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, WB_ERR_S_HSV_20, WB_ERR_S_HSV_21, WB_ERR_S_HSV_22, WB_ERR_S_HSV_23)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, maxofList4, float(WB_ERR_S_20), float(WB_ERR_S_21), float(WB_ERR_S_22), float(WB_ERR_S_23))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
        elif card_metric_value_id[2] == '各色块对应的饱和度S值的平均值':
            WB_ERR_S_20 = WB_ERR_S_21 = WB_ERR_S_22 = WB_ERR_S_23 = 0
            list4 = []
            for index in range(len(rows)):
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == '20':
                    WB_ERR_S_20 = rows[index][9]
                    WB_ERR_S_21 = rows[index + 1][9]
                    WB_ERR_S_22 = rows[index + 2][9]
                    WB_ERR_S_23 = rows[index + 3][9]
                    list4.append(float(WB_ERR_S_20))
                    list4.append(float(WB_ERR_S_21))
                    list4.append(float(WB_ERR_S_22))
                    list4.append(float(WB_ERR_S_23))
                    break
            meanofList4 = 0
            sum = 0
            for item in list4:
                sum += float(item)
            meanofList4 = sum / len(list4)
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(各色块对应的饱和度S值的平均值)"""\
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_4(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, WB_ERR_S_HSV_20, WB_ERR_S_HSV_21, WB_ERR_S_HSV_22, WB_ERR_S_HSV_23)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, meanofList4, float(WB_ERR_S_20), float(WB_ERR_S_21), float(WB_ERR_S_22), float(WB_ERR_S_23))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] == '1-18色块色彩饱和度':
            print '1-18色块色彩饱和度'
            listpair = []
            listpair_ideal = []
            for index in range(len(rows)):
                if len(rows[index]) == 0:
                    continue
                if rows[index][0] == 'SNR_BW (dB; RGBY)':
                    for i in range(24):
                        ai = rows[index + 3 + i][8]
                        bi = rows[index + 3 + i][9]
                        ai_ideal = rows[index + 3 + i][11]
                        bi_ideal = rows[index + 3 + i][12]
                        list_tmp = []
                        list_tmp.append(ai)
                        list_tmp.append(bi)
                        listpair.append(list_tmp)
                        list_ideal_tmp = []
                        list_ideal_tmp.append(ai_ideal)
                        list_ideal_tmp.append(bi_ideal)
                        listpair_ideal.append(list_ideal_tmp)
                    break

            resmeas = 0
            idealmeas = 0
            for i in range(24):
                resmeas += math.sqrt(float(listpair[i][0]) * float(listpair[i][0]) + float(listpair[i][1]) * float(listpair[i][1]))
                idealmeas += math.sqrt(float(listpair_ideal[i][0]) * float(listpair_ideal[i][0]) + float(listpair_ideal[i][1]) * float(listpair_ideal[i][1]))
            resmeas = resmeas / idealmeas

            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(各1-18色块色彩饱和度)""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            #需要加上48个信息的表
            rating_insert = """INSERT INTO rating_single_48(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, 1_a_meas, 1_b_meas, 2_a_meas, 2_b_meas, 3_a_meas, 3_b_meas, 4_a_meas, 4_b_meas, 5_a_meas, 5_b_meas, 6_a_meas, 6_b_meas, 7_a_meas, 7_b_meas, 8_a_meas, 8_b_meas, 9_a_meas, 9_b_meas, 10_a_meas, 10_b_meas, 11_a_meas, 11_b_meas, 12_a_meas, 12_b_meas, 13_a_meas, 13_b_meas, 14_a_meas, 14_b_meas, 15_a_meas, 15_b_meas, 16_a_meas, 16_b_meas, 17_a_meas, 17_b_meas, 18_a_meas, 18_b_meas, 19_a_meas, 19_b_meas, 20_a_meas, 20_b_meas, 21_a_meas, 21_b_meas, 22_a_meas, 22_b_meas, 23_a_meas, 23_b_meas, 24_a_meas, 24_b_meas)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f,  %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, resmeas, float(listpair[0][0]), float(listpair[0][1]),  float(listpair[1][0]), float(listpair[1][1]), float(listpair[2][0]), float(listpair[2][1]), float(listpair[3][0]), float(listpair[3][1]), float(listpair[4][0]), float(listpair[4][1]), float(listpair[5][0]), float(listpair[5][1]), float(listpair[6][0]), float(listpair[6][1]), float(listpair[7][0]), float(listpair[7][1]), float(listpair[8][0]), float(listpair[8][1]), float(listpair[9][0]), float(listpair[9][1]), float(listpair[10][0]), float(listpair[10][1]), float(listpair[11][0]), float(listpair[11][1]), float(listpair[12][0]), float(listpair[12][1]), float(listpair[13][0]), float(listpair[13][1]), float(listpair[14][0]), float(listpair[14][1]), float(listpair[15][0]), float(listpair[15][1]), float(listpair[16][0]), float(listpair[16][1]), float(listpair[17][0]), float(listpair[17][1]), float(listpair[18][0]), float(listpair[18][1]), float(listpair[19][0]), float(listpair[19][1]), float(listpair[20][0]), float(listpair[20][1]), float(listpair[21][0]), float(listpair[21][1]), float(listpair[22][0]), float(listpair[22][1]), float(listpair[23][0]), float(listpair[23][1]))
            #print rating_insert
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] == '各色块对应Delta-E*ab的平均值':
            list24 = []
            print rows
            for index in range(50, len(rows)):
                if len(rows[index]) == 0 :
                    continue
                if rows[index][1] == 'Delta-E*ab':
                    for i in range(24):
                        list24.append(float(rows[index + 1 + i][1]))
                    break
            sum = 0
            for item in list24:
                sum += float(item)
            meanofList24 = sum / len(list24)

            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(各色块对应Delta-E*ab的平均值)""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            #需要加上48个信息的表
            rating_insert = """INSERT INTO rating_single_24(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, 1_Delta_E_ab, 2_Delta_E_ab, 3_Delta_E_ab, 4_Delta_E_ab, 5_Delta_E_ab, 6_Delta_E_ab, 7_Delta_E_ab, 8_Delta_E_ab, 9_Delta_E_ab, 10_Delta_E_ab, 11_Delta_E_ab, 12_Delta_E_ab, 13_Delta_E_ab, 14_Delta_E_ab, 15_Delta_E_ab, 16_Delta_E_ab, 17_Delta_E_ab, 18_Delta_E_ab, 19_Delta_E_ab, 20_Delta_E_ab, 21_Delta_E_ab, 22_Delta_E_ab, 23_Delta_E_ab, 24_Delta_E_ab)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, meanofList24, float(list24[0]), float(list24[1]),float(list24[2]),float(list24[3]),float(list24[4]),float(list24[5]),float(list24[6]),float(list24[7]),float(list24[8]),float(list24[9]),float(list24[10]),float(list24[11]),float(list24[12]),float(list24[13]),float(list24[14]),float(list24[15]),float(list24[16]),float(list24[17]),float(list24[18]),float(list24[19]),float(list24[20]),float(list24[21]),float(list24[22]), float(list24[23]))
            print rating_insert
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] == '各色块对应Delta-E*ab的最大值':
            list24 = []
            for index in range(50, len(rows)):
                if len(rows[index]) == 0:
                    continue
                if rows[index][1] == 'Delta-E*ab':
                    for i in range(24):
                        list24.append(float(rows[index + 1 + i][1]))
                    break
            maxofList24 = max(list24)
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(各色块对应Delta-E*ab的最大值)""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            #需要加上24个信息的表
            rating_insert = """INSERT INTO rating_single_24(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, 1_Delta_E_ab, 2_Delta_E_ab, 3_Delta_E_ab, 4_Delta_E_ab, 5_Delta_E_ab, 6_Delta_E_ab, 7_Delta_E_ab, 8_Delta_E_ab, 9_Delta_E_ab, 10_Delta_E_ab, 11_Delta_E_ab, 12_Delta_E_ab, 13_Delta_E_ab, 14_Delta_E_ab, 15_Delta_E_ab, 16_Delta_E_ab, 17_Delta_E_ab, 18_Delta_E_ab, 19_Delta_E_ab, 20_Delta_E_ab, 21_Delta_E_ab, 22_Delta_E_ab, 23_Delta_E_ab, 24_Delta_E_ab)
                                      VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f)
                """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, meanofList24, float(list24[0]), float(list24[1]),float(list24[2]),float(list24[3]),float(list24[4]),float(list24[5]),float(list24[6]),float(list24[7]),float(list24[8]),float(list24[9]),float(list24[10]),float(list24[11]),float(list24[12]),float(list24[13]),float(list24[14]),float(list24[15]),float(list24[16]),float(list24[17]),float(list24[18]),float(list24[19]),float(list24[20]),float(list24[21]),float(list24[22]), float(list24[23]))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
def handleTE270(inf, conn, rootpath):
    print "handlete270"
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric, value FROM card_metric_value_group
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    cursor.execute(cardAndetric_query)
    card_metric_value_set = cursor.fetchall()
    for card_metric_value_id in card_metric_value_set:
        resfilename = """%s_%s_%s_%s_%s_%s_%s_1_oecf_average.txt""" \
                      %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6])

        respath = rootpath + "/Results/" + resfilename
        lab = (rootpath.split("/"))[-1]
        distance = inf[6]
        #print open_txt(respath)
        rows = open_txt(respath)
        #print rows
        vn_1 = 0
        DR_total = 0
        list20 = []
        for row in rows:
            if len(row) == 0:
                continue
            if row[0] == 'SNR_total':
                vn_1 = float(row[3])
                DR_total = float(row[6])
                break
        for index in range(51, len(rows)):
            if len(rows[index]) == 0:
                continue
            if rows[index][1] and rows[index][1] == ' VN (1)  ':
                for i in range(1, 21):
                    list20.append(float(rows[index + i][1]))
                break
        if card_metric_value_id[2] == 'DR_total[f-stop]':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(DR_total[f-stop])""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, Ori_CPIQ)
                              VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f)
                              """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, DR_total, DR_total)
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
        elif card_metric_value_id[2] == 'VN1_average ignore First2/Last2(computer display )':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(VN1_average ignore First2/Last2(computer display ))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, Ori_CPIQ)
                              VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f)
                              """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, vn_1, vn_1)
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
        elif card_metric_value_id[2] == 'VN1_average of NONZERO(computer display )':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(VN1_average of NONZERO(computer display ))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            cnt = 0
            sumofList20 = 0
            for item in list20:
                if item != 0:
                    cnt = cnt + 1
                    sumofList20 += item
            meanofNonZeroList20 = sumofList20 / cnt
            print  meanofNonZeroList20
            print list20
            rating_insert = """INSERT INTO rating_single_20(graph_path, cellphone_id, light_source_id, card_metric_value_id, lab, distance, CPIQ, OECF20, OECF19, OECF18, OECF17, OECF16, OECF15, OECF14, OECF13, OECF12, OECF11, OECF10, OECF9, OECF8, OECF7, OECF6, OECF5, OECF4, OECF3, OECF2, OECF1)
                              VALUES ("%s", %d, %s, %d, "%s", "%s", %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f, %f)
                              """%(graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), lab, distance, meanofNonZeroList20, list20[0],list20[1],list20[2],list20[3],list20[4],list20[5],list20[6],list20[7],list20[8],list20[9],list20[10],list20[11],list20[12],list20[13],list20[14],list20[15],list20[16],list20[17],list20[18],list20[19])
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
def handleTE268(inf, conn, rootpath):
    print "handleTE268"
    #如果包含left或right,那么不处理这个图片
    if "left" in inf[6] or "right" in inf[6]:
        return
    relatedfilename = """%s_%s_%s_%s_%s_%s_%s right_%s_resolution.txt""" \
                  %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
    flag_is16ornot = 0
    if os.path.isfile(rootpath + "/Results/" + relatedfilename):
        flag_is16ornot = 1
    light_cell_ret = dealWithForeignKey(inf, conn, rootpath)
    light_source_id = light_cell_ret[0]
    cellphone_id = light_cell_ret[1]
    cursor = light_cell_ret[2]
    cardAndetric_query = """SELECT physical_id, metric, value FROM card_metric_value_group
                          WHERE card = '%s'"""%(inf[2])
    #print cardAndetric_query
    cursor.execute(cardAndetric_query)
    card_metric_value_set = cursor.fetchall()
    resfilename = """%s_%s_%s_%s_%s_%s_%s_%s_resolution.txt""" \
                  %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])

    respath = rootpath + "/Results/" + resfilename
    lab = (rootpath.split("/"))[-1]
    distance = inf[6]
    rows = open_txt(respath)
    list1_10 = []
    list2_10 = []
    list3_10 = []
    list4_10 = []
    list5_10 = []
    list6_10 = []
    list7_10 = []
    list8_10 = []
    list1_30 = []
    list2_30 = []
    list3_30 = []
    list4_30 = []
    list5_30 = []
    list6_30 = []
    list7_30 = []
    list8_30 = []
    list1_50 = []
    list2_50 = []
    list3_50 = []
    list4_50 = []
    list5_50 = []
    list6_50 = []
    list7_50 = []
    list8_50 = []
    count = 0
    for index in range(len(rows)):
        if len(rows[index]) == 0:
            continue
        if rows[index][0] == 'Sub':
            if count < 3:
                if count == 0:
                    for i in range(1, 26):
                        list1_10.append(float(rows[index + i][2]))
                        list2_10.append(float(rows[index + i][3]))
                        list3_10.append(float(rows[index + i][4]))
                        list4_10.append(float(rows[index + i][5]))
                        list5_10.append(float(rows[index + i][6]))
                        list6_10.append(float(rows[index + i][7]))
                        list7_10.append(float(rows[index + i][8]))
                        list8_10.append(float(rows[index + i][9]))
                    count = count + 1

                elif count == 1:
                    for i in range(1, 26):
                        list1_30.append(float(rows[index + i][2]))
                        list2_30.append(float(rows[index + i][3]))
                        list3_30.append(float(rows[index + i][4]))
                        list4_30.append(float(rows[index + i][5]))
                        list5_30.append(float(rows[index + i][6]))
                        list6_30.append(float(rows[index + i][7]))
                        list7_30.append(float(rows[index + i][8]))
                        list8_30.append(float(rows[index + i][9]))
                    count = count + 1
                elif count == 2:
                    for i in range(1, 26):
                        list1_50.append(float(rows[index + i][2]))
                        list2_50.append(float(rows[index + i][3]))
                        list3_50.append(float(rows[index + i][4]))
                        list4_50.append(float(rows[index + i][5]))
                        list5_50.append(float(rows[index + i][6]))
                        list6_50.append(float(rows[index + i][7]))
                        list7_50.append(float(rows[index + i][8]))
                        list8_50.append(float(rows[index + i][9]))
                    break
    print len(list3_30)
    #三张表各自的总和
    sumofMTF10 = sumofMTF30 = sumofMTF50 = 0
    #为了求最小值
    sumofMTF10_1_5 = sumofMTF10_2_6 = sumofMTF10_3_7 = sumofMTF10_4_8 = 0
    sumofMTF30_1_5 = sumofMTF30_2_6 = sumofMTF30_3_7 = sumofMTF30_4_8 = 0
    sumofMTF50_1_5 = sumofMTF50_2_6 = sumofMTF50_3_7 = sumofMTF50_4_8 = 0
    #中心星总和
    sumofCenterStar_10 = 0
    sumofCenterStar_30 = 0
    sumofCenterStar_50 = 0
    #四角星总和
    sumofFourAngleStar_10 = 0
    sumofFourAngleStar_30 = 0
    sumofFourAngleStar_50 = 0
    for i in range(25):
        sumofMTF10 = sumofMTF10 + list1_10[i] +list2_10[i] +list3_10[i] +list4_10[i] +list5_10[i] +list6_10[i] +list7_10[i] +list8_10[i]
        sumofMTF30 = sumofMTF30 + list1_30[i] +list2_30[i] +list3_30[i] +list4_30[i] +list5_30[i] +list6_30[i] +list7_30[i] +list8_30[i]
        sumofMTF50 = sumofMTF50 + list1_50[i] +list2_50[i] +list3_50[i] +list4_50[i] +list5_50[i] +list6_50[i] +list7_50[i] +list8_50[i]

        sumofMTF10_1_5 = sumofMTF10_1_5 + list1_10[i] + list5_10[i]
        sumofMTF10_2_6 = sumofMTF10_2_6 + list2_10[i] + list6_10[i]
        sumofMTF10_3_7 = sumofMTF10_3_7 + list3_10[i] + list7_10[i]
        sumofMTF10_4_8 = sumofMTF10_4_8 + list4_10[i] + list8_10[i]

        sumofMTF30_1_5 = sumofMTF30_1_5 + list1_30[i] + list5_30[i]
        sumofMTF30_2_6 = sumofMTF30_2_6 + list2_30[i] + list6_30[i]
        sumofMTF30_3_7 = sumofMTF30_3_7 + list3_30[i] + list7_30[i]
        sumofMTF30_4_8 = sumofMTF30_4_8 + list4_30[i] + list8_30[i]

        sumofMTF50_1_5 = sumofMTF50_1_5 + list1_50[i] + list5_50[i]
        sumofMTF50_2_6 = sumofMTF50_2_6 + list2_50[i] + list6_50[i]
        sumofMTF50_3_7 = sumofMTF50_3_7 + list3_50[i] + list7_50[i]
        sumofMTF50_4_8 = sumofMTF50_4_8 + list4_50[i] + list8_50[i]
        if i == 0:
            sumofCenterStar_10 = sumofCenterStar_10 + list1_10[i] + list2_10[i] + list3_10[i] + list4_10[i] + list5_10[i] + list6_10[i] + list7_10[i] + list8_10[i]
            sumofCenterStar_30 = sumofCenterStar_30 + list1_30[i] + list2_30[i] + list3_30[i] + list4_30[i] + list5_30[i] + list6_30[i] + list7_30[i] + list8_30[i]
            sumofCenterStar_50 = sumofCenterStar_50 + list1_50[i] + list2_50[i] + list3_50[i] + list4_50[i] + list5_50[i] + list6_50[i] + list7_50[i] + list8_50[i]
        if i == 10 or i == 14 or i == 18 or i == 22:
            sumofFourAngleStar_10 = sumofFourAngleStar_10 + list1_10[i] + list2_10[i] + list3_10[i] + list4_10[i] + list5_10[i] + list6_10[i] + list7_10[i] + list8_10[i]
            sumofFourAngleStar_30 = sumofFourAngleStar_30 + list1_30[i] + list2_30[i] + list3_30[i] + list4_30[i] + list5_30[i] + list6_30[i] + list7_30[i] + list8_30[i]
            sumofFourAngleStar_50 = sumofFourAngleStar_50 + list1_50[i] + list2_50[i] + list3_50[i] + list4_50[i] + list5_50[i] + list6_50[i] + list7_50[i] + list8_50[i]

    meanofMTF10 = sumofMTF10 / (len(list1_10) * 8) * 2
    meanofMTF30 = sumofMTF30 / (len(list1_10) * 8) * 2
    meanofMTF50 = sumofMTF50 / (len(list1_10) * 8) * 2

    meanofMTF10_1_5 = sumofMTF10_1_5 / (len(list1_10) * 2)
    meanofMTF10_2_6 = sumofMTF10_2_6 / (len(list1_10) * 2)
    meanofMTF10_3_7 = sumofMTF10_3_7 / (len(list1_10) * 2)
    meanofMTF10_4_8 = sumofMTF10_4_8 / (len(list1_10) * 2)
    listMeanofMTF10 = []
    listMeanofMTF10.append(meanofMTF10_1_5)
    listMeanofMTF10.append(meanofMTF10_2_6)
    listMeanofMTF10.append(meanofMTF10_3_7)
    listMeanofMTF10.append(meanofMTF10_4_8)

    meanofMTF30_1_5 = sumofMTF30_1_5 / (len(list1_10) * 2)
    meanofMTF30_2_6 = sumofMTF30_2_6 / (len(list1_10) * 2)
    meanofMTF30_3_7 = sumofMTF30_3_7 / (len(list1_10) * 2)
    meanofMTF30_4_8 = sumofMTF30_4_8 / (len(list1_10) * 2)
    listMeanofMTF30 = []
    listMeanofMTF30.append(meanofMTF30_1_5)
    listMeanofMTF30.append(meanofMTF30_2_6)
    listMeanofMTF30.append(meanofMTF30_3_7)
    listMeanofMTF30.append(meanofMTF30_4_8)

    meanofMTF50_1_5 = sumofMTF50_1_5 / (len(list1_10) * 2)
    meanofMTF50_2_6 = sumofMTF50_2_6 / (len(list1_10) * 2)
    meanofMTF50_3_7 = sumofMTF50_3_7 / (len(list1_10) * 2)
    meanofMTF50_4_8 = sumofMTF50_4_8 / (len(list1_10) * 2)
    listMeanofMTF50 = []
    listMeanofMTF50.append(meanofMTF50_1_5)
    listMeanofMTF50.append(meanofMTF50_2_6)
    listMeanofMTF50.append(meanofMTF50_3_7)
    listMeanofMTF50.append(meanofMTF50_4_8)

    minofMTF10 = min(listMeanofMTF10) * 2
    minofMTF30 = min(listMeanofMTF30) * 2
    minofMTF50 = min(listMeanofMTF50) * 2
    meanofCenterStar_10 = sumofCenterStar_10 / 8 * 2
    meanofCenterStar_30 = sumofCenterStar_30 / 8 * 2
    meanofCenterStar_50 = sumofCenterStar_50 / 8 * 2
    meanofFourAngleStar_10 = sumofFourAngleStar_10 / (4 * 8) * 2
    meanofFourAngleStar_30 = sumofFourAngleStar_30 / (4 * 8) * 2
    meanofFourAngleStar_50 = sumofFourAngleStar_50 / (4 * 8) * 2

    if flag_is16ornot:
        leftfilename = """%s_%s_%s_%s_%s_%s_%s left_%s_resolution.txt""" \
                  %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
        rightfilename = """%s_%s_%s_%s_%s_%s_%s right_%s_resolution.txt""" \
                       %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7][0])
        left_rows = open_txt(rootpath + "/Results/" + leftfilename)
        right_rows = open_txt(rootpath + "/Results/" + rightfilename)
        list1_10_left = []
        list2_10_left = []
        list3_10_left = []
        list4_10_left = []
        list5_10_left = []
        list6_10_left = []
        list7_10_left = []
        list8_10_left = []
        list1_30_left = []
        list2_30_left = []
        list3_30_left = []
        list4_30_left = []
        list5_30_left = []
        list6_30_left = []
        list7_30_left = []
        list8_30_left = []
        list1_50_left = []
        list2_50_left = []
        list3_50_left = []
        list4_50_left = []
        list5_50_left = []
        list6_50_left = []
        list7_50_left = []
        list8_50_left = []
        list1_10_right = []
        list2_10_right = []
        list3_10_right = []
        list4_10_right = []
        list5_10_right = []
        list6_10_right = []
        list7_10_right = []
        list8_10_right = []
        list1_30_right = []
        list2_30_right = []
        list3_30_right = []
        list4_30_right = []
        list5_30_right = []
        list6_30_right = []
        list7_30_right = []
        list8_30_right = []
        list1_50_right = []
        list2_50_right = []
        list3_50_right = []
        list4_50_right = []
        list5_50_right = []
        list6_50_right = []
        list7_50_right = []
        list8_50_right = []
        count = 0
        for index in range(len(left_rows)):
            if len(left_rows[index]) == 0:
                continue
            if left_rows[index][0] == 'Sub':
                if count < 3:
                    if count == 0:
                        for i in range(1, 26):
                            if i == 16 or i == 17 or i == 18 or i == 19 or i == 20:
                                list1_10_left.append(float(left_rows[index + i][2]))
                                list2_10_left.append(float(left_rows[index + i][3]))
                                list3_10_left.append(float(left_rows[index + i][4]))
                                list4_10_left.append(float(left_rows[index + i][5]))
                                list5_10_left.append(float(left_rows[index + i][6]))
                                list6_10_left.append(float(left_rows[index + i][7]))
                                list7_10_left.append(float(left_rows[index + i][8]))
                                list8_10_left.append(float(left_rows[index + i][9]))
                        count = count + 1
                    elif count == 1:
                        for i in range(1, 26):
                            if i == 16 or i == 17 or i == 18 or i == 19 or i == 20:
                                list1_30_left.append(float(left_rows[index + i][2]))
                                list2_30_left.append(float(left_rows[index + i][3]))
                                list3_30_left.append(float(left_rows[index + i][4]))
                                list4_30_left.append(float(left_rows[index + i][5]))
                                list5_30_left.append(float(left_rows[index + i][6]))
                                list6_30_left.append(float(left_rows[index + i][7]))
                                list7_30_left.append(float(left_rows[index + i][8]))
                                list8_30_left.append(float(left_rows[index + i][9]))
                        count = count + 1
                    elif count == 2:
                        for i in range(1, 26):
                            if i == 16 or i == 17 or i == 18 or i == 19 or i == 20:
                                list1_50_left.append(float(left_rows[index + i][2]))
                                list2_50_left.append(float(left_rows[index + i][3]))
                                list3_50_left.append(float(left_rows[index + i][4]))
                                list4_50_left.append(float(left_rows[index + i][5]))
                                list5_50_left.append(float(left_rows[index + i][6]))
                                list6_50_left.append(float(left_rows[index + i][7]))
                                list7_50_left.append(float(left_rows[index + i][8]))
                                list8_50_left.append(float(left_rows[index + i][9]))
                        break
        count = 0
        for index in range(len(right_rows)):
            if len(right_rows[index]) == 0:
                continue
            if right_rows[index][0] == 'Sub':
                if count < 3:
                    if count == 0:
                        for i in range(1, 26):
                            if i == 10 or i == 11 or i == 12 or i == 24 or i == 25:
                                list1_10_right.append(float(right_rows[index + i][2]))
                                list2_10_right.append(float(right_rows[index + i][3]))
                                list3_10_right.append(float(right_rows[index + i][4]))
                                list4_10_right.append(float(right_rows[index + i][5]))
                                list5_10_right.append(float(right_rows[index + i][6]))
                                list6_10_right.append(float(right_rows[index + i][7]))
                                list7_10_right.append(float(right_rows[index + i][8]))
                                list8_10_right.append(float(right_rows[index + i][9]))
                        count = count + 1
                    elif count == 1:
                        for i in range(1, 26):
                            if i == 10 or i == 11 or i == 12 or i == 24 or i == 25:
                                list1_30_right.append(float(right_rows[index + i][2]))
                                list2_30_right.append(float(right_rows[index + i][3]))
                                list3_30_right.append(float(right_rows[index + i][4]))
                                list4_30_right.append(float(right_rows[index + i][5]))
                                list5_30_right.append(float(right_rows[index + i][6]))
                                list6_30_right.append(float(right_rows[index + i][7]))
                                list7_30_right.append(float(right_rows[index + i][8]))
                                list8_30_right.append(float(right_rows[index + i][9]))
                        count = count + 1
                    elif count == 2:
                        for i in range(1, 26):
                            if i == 10 or i == 11 or i == 12 or i == 24 or i == 25:
                                list1_50_right.append(float(right_rows[index + i][2]))
                                list2_50_right.append(float(right_rows[index + i][3]))
                                list3_50_right.append(float(right_rows[index + i][4]))
                                list4_50_right.append(float(right_rows[index + i][5]))
                                list5_50_right.append(float(right_rows[index + i][6]))
                                list6_50_right.append(float(right_rows[index + i][7]))
                                list7_50_right.append(float(right_rows[index + i][8]))
                                list8_50_right.append(float(right_rows[index + i][9]))
                        break
        sumofMTF10_left = sumofMTF30_left = sumofMTF50_left = 0
        sumofMTF10_right = sumofMTF30_right = sumofMTF50_right = 0

        sumofMTF10_left_1_5 = sumofMTF10_left_2_6 = sumofMTF10_left_3_7 = sumofMTF10_left_4_8 = 0
        sumofMTF30_left_1_5 = sumofMTF30_left_2_6 = sumofMTF30_left_3_7 = sumofMTF30_left_4_8 = 0
        sumofMTF50_left_1_5 = sumofMTF50_left_2_6 = sumofMTF50_left_3_7 = sumofMTF50_left_4_8 = 0

        sumofMTF10_right_1_5 = sumofMTF10_right_2_6 = sumofMTF10_right_3_7 = sumofMTF10_right_4_8 = 0
        sumofMTF30_right_1_5 = sumofMTF30_right_2_6 = sumofMTF30_right_3_7 = sumofMTF30_right_4_8 = 0
        sumofMTF50_right_1_5 = sumofMTF50_right_2_6 = sumofMTF50_right_3_7 = sumofMTF50_right_4_8 = 0

        sumofFourAngleStar_10= sumofFourAngleStar_30= sumofFourAngleStar_50= 0
        for i in range(5):
            sumofMTF10_left = sumofMTF10_left + list1_10_left[i] + list2_10_left[i] + list3_10_left[i] + list4_10_left[i] + list5_10_left[i] + list6_10_left[i] + list7_10_left[i] + list8_10_left[i]
            sumofMTF30_left = sumofMTF30_left + list1_30_left[i] + list2_30_left[i] + list3_30_left[i] + list4_30_left[i] + list5_30_left[i] + list6_30_left[i] + list7_30_left[i] + list8_30_left[i]
            sumofMTF50_left = sumofMTF50_left + list1_50_left[i] + list2_50_left[i] + list3_50_left[i] + list4_50_left[i] + list5_50_left[i] + list6_50_left[i] + list7_50_left[i] + list8_50_left[i]

            sumofMTF10_right = sumofMTF10_right + list1_10_right[i] + list2_10_right[i] + list3_10_right[i] + list4_10_right[i] + list5_10_right[i] + list6_10_right[i] + list7_10_right[i] + list8_10_right[i]
            sumofMTF30_right = sumofMTF30_right + list1_30_right[i] + list2_30_right[i] + list3_30_right[i] + list4_30_right[i] + list5_30_right[i] + list6_30_right[i] + list7_30_right[i] + list8_30_right[i]
            sumofMTF50_right = sumofMTF50_right + list1_50_right[i] + list2_50_right[i] + list3_50_right[i] + list4_50_right[i] + list5_50_right[i] + list6_50_right[i] + list7_50_right[i] + list8_50_right[i]

            sumofMTF10_left_1_5 = sumofMTF10_left_1_5 + list1_10_left[i] + list5_10_left[i]
            sumofMTF10_left_2_6 = sumofMTF10_left_2_6 + list2_10_left[i] + list6_10_left[i]
            sumofMTF10_left_3_7 = sumofMTF10_left_3_7 + list3_10_left[i] + list7_10_left[i]
            sumofMTF10_left_4_8 = sumofMTF10_left_4_8 + list4_10_left[i] + list8_10_left[i]

            sumofMTF10_right_1_5 = sumofMTF10_right_1_5 + list1_10_right[i] + list5_10_right[i]
            sumofMTF10_right_2_6 = sumofMTF10_right_2_6 + list2_10_right[i] + list6_10_right[i]
            sumofMTF10_right_3_7 = sumofMTF10_right_3_7 + list3_10_right[i] + list7_10_right[i]
            sumofMTF10_right_4_8 = sumofMTF10_right_4_8 + list4_10_right[i] + list8_10_right[i]

            sumofMTF30_left_1_5 = sumofMTF30_left_1_5 + list1_30_left[i] + list5_30_left[i]
            sumofMTF30_left_2_6 = sumofMTF30_left_2_6 + list2_30_left[i] + list6_30_left[i]
            sumofMTF30_left_3_7 = sumofMTF30_left_3_7 + list3_30_left[i] + list7_30_left[i]
            sumofMTF30_left_4_8 = sumofMTF30_left_4_8 + list4_30_left[i] + list8_30_left[i]

            sumofMTF30_right_1_5 = sumofMTF30_right_1_5 + list1_30_right[i] + list5_30_right[i]
            sumofMTF30_right_2_6 = sumofMTF30_right_2_6 + list2_30_right[i] + list6_30_right[i]
            sumofMTF30_right_3_7 = sumofMTF30_right_3_7 + list3_30_right[i] + list7_30_right[i]
            sumofMTF30_right_4_8 = sumofMTF30_right_4_8 + list4_30_right[i] + list8_30_right[i]

            sumofMTF50_left_1_5 = sumofMTF50_left_1_5 + list1_50_left[i] + list5_50_left[i]
            sumofMTF50_left_2_6 = sumofMTF50_left_2_6 + list2_50_left[i] + list6_50_left[i]
            sumofMTF50_left_3_7 = sumofMTF50_left_3_7 + list3_50_left[i] + list7_50_left[i]
            sumofMTF50_left_4_8 = sumofMTF50_left_4_8 + list4_50_left[i] + list8_50_left[i]

            sumofMTF50_right_1_5 = sumofMTF50_right_1_5 + list1_50_right[i] + list5_50_right[i]
            sumofMTF50_right_2_6 = sumofMTF50_right_2_6 + list2_50_right[i] + list6_50_right[i]
            sumofMTF50_right_3_7 = sumofMTF50_right_3_7 + list3_50_right[i] + list7_50_right[i]
            sumofMTF50_right_4_8 = sumofMTF50_right_4_8 + list4_50_right[i] + list8_50_right[i]
            if i != 1:
                if i == 0 or i == 4:
                    sumofFourAngleStar_10 = sumofFourAngleStar_10 + list1_10_left[i] + list2_10_left[i] + list3_10_left[i] + list4_10_left[i] + list5_10_left[i] + list6_10_left[i] + list7_10_left[i] + list8_10_left[i]
                    sumofFourAngleStar_30 = sumofFourAngleStar_30 + list1_30_left[i] + list2_30_left[i] + list3_30_left[i] + list4_30_left[i] + list5_30_left[i] + list6_30_left[i] + list7_30_left[i] + list8_30_left[i]
                    sumofFourAngleStar_50 = sumofFourAngleStar_50 + list1_50_left[i] + list2_50_left[i] + list3_50_left[i] + list4_50_left[i] + list5_50_left[i] + list6_50_left[i] + list7_50_left[i] + list8_50_left[i]

                if i == 2 or i == 3:
                    sumofFourAngleStar_10 = sumofFourAngleStar_10 + list1_10_right[i] + list2_10_right[i] + list3_10_right[i] + list4_10_right[i] + list5_10_right[i] + list6_10_right[i] + list7_10_right[i] + list8_10_right[i]
                    sumofFourAngleStar_30 = sumofFourAngleStar_30 + list1_30_right[i] + list2_30_right[i] + list3_30_right[i] + list4_30_right[i] + list5_30_right[i] + list6_30_right[i] + list7_30_right[i] + list8_30_right[i]
                    sumofFourAngleStar_50 = sumofFourAngleStar_50 + list1_50_right[i] + list2_50_right[i] + list3_50_right[i] + list4_50_right[i] + list5_50_right[i] + list6_50_right[i] + list7_50_right[i] + list8_50_right[i]
        meanofMTF10 = (sumofMTF10 + sumofMTF10_left + sumofMTF10_right) / (len(list1_10) * 8 + len(list1_10_left) * 8 * 2) * 2
        meanofMTF30 = (sumofMTF30 + sumofMTF30_left + sumofMTF30_right) / (len(list1_10) * 8 + len(list1_10_left) * 8 * 2) * 2
        meanofMTF50 = (sumofMTF50 + sumofMTF50_left + sumofMTF50_right) / (len(list1_10) * 8 + len(list1_10_left) * 8 * 2) * 2

        meanofMTF10_1_5_left = sumofMTF10_left_1_5 / (len(list1_10_left) * 2)
        meanofMTF10_2_6_left = sumofMTF10_left_2_6 / (len(list1_10_left) * 2)
        meanofMTF10_3_7_left = sumofMTF10_left_3_7 / (len(list1_10_left) * 2)
        meanofMTF10_4_8_left = sumofMTF10_left_4_8 / (len(list1_10_left) * 2)
        meanofMTF10_1_5_right = sumofMTF10_right_1_5 / (len(list1_10_right) * 2)
        meanofMTF10_2_6_right = sumofMTF10_right_2_6 / (len(list1_10_right) * 2)
        meanofMTF10_3_7_right = sumofMTF10_right_3_7 / (len(list1_10_right) * 2)
        meanofMTF10_4_8_right = sumofMTF10_right_4_8 / (len(list1_10_right) * 2)
        listMeanofMTF10.append(meanofMTF10_1_5_left)
        listMeanofMTF10.append(meanofMTF10_2_6_left)
        listMeanofMTF10.append(meanofMTF10_3_7_left)
        listMeanofMTF10.append(meanofMTF10_4_8_left)
        listMeanofMTF10.append(meanofMTF10_1_5_right)
        listMeanofMTF10.append(meanofMTF10_2_6_right)
        listMeanofMTF10.append(meanofMTF10_3_7_right)
        listMeanofMTF10.append(meanofMTF10_4_8_right)

        meanofMTF30_1_5_left = sumofMTF30_left_1_5 / (len(list1_10_left) * 2)
        meanofMTF30_2_6_left = sumofMTF30_left_2_6 / (len(list1_10_left) * 2)
        meanofMTF30_3_7_left = sumofMTF30_left_3_7 / (len(list1_10_left) * 2)
        meanofMTF30_4_8_left = sumofMTF30_left_4_8 / (len(list1_10_left) * 2)
        meanofMTF30_1_5_right = sumofMTF30_right_1_5 / (len(list1_10_right) * 2)
        meanofMTF30_2_6_right = sumofMTF30_right_2_6 / (len(list1_10_right) * 2)
        meanofMTF30_3_7_right = sumofMTF30_right_3_7 / (len(list1_10_right) * 2)
        meanofMTF30_4_8_right = sumofMTF30_right_4_8 / (len(list1_10_right) * 2)
        listMeanofMTF30.append(meanofMTF30_1_5_left)
        listMeanofMTF30.append(meanofMTF30_2_6_left)
        listMeanofMTF30.append(meanofMTF30_3_7_left)
        listMeanofMTF30.append(meanofMTF30_4_8_left)
        listMeanofMTF30.append(meanofMTF30_1_5_right)
        listMeanofMTF30.append(meanofMTF30_2_6_right)
        listMeanofMTF30.append(meanofMTF30_3_7_right)
        listMeanofMTF30.append(meanofMTF30_4_8_right)

        meanofMTF50_1_5_left = sumofMTF50_left_1_5 / (len(list1_10_left) * 2)
        meanofMTF50_2_6_left = sumofMTF50_left_2_6 / (len(list1_10_left) * 2)
        meanofMTF50_3_7_left = sumofMTF50_left_3_7 / (len(list1_10_left) * 2)
        meanofMTF50_4_8_left = sumofMTF50_left_4_8 / (len(list1_10_left) * 2)
        meanofMTF50_1_5_right = sumofMTF50_right_1_5 / (len(list1_10_right) * 2)
        meanofMTF50_2_6_right = sumofMTF50_right_2_6 / (len(list1_10_right) * 2)
        meanofMTF50_3_7_right = sumofMTF50_right_3_7 / (len(list1_10_right) * 2)
        meanofMTF50_4_8_right = sumofMTF50_right_4_8 / (len(list1_10_right) * 2)
        listMeanofMTF50.append(meanofMTF50_1_5_left)
        listMeanofMTF50.append(meanofMTF50_2_6_left)
        listMeanofMTF50.append(meanofMTF50_3_7_left)
        listMeanofMTF50.append(meanofMTF50_4_8_left)
        listMeanofMTF50.append(meanofMTF50_1_5_right)
        listMeanofMTF50.append(meanofMTF50_2_6_right)
        listMeanofMTF50.append(meanofMTF50_3_7_right)
        listMeanofMTF50.append(meanofMTF50_4_8_right)

        minofMTF10 = min(listMeanofMTF10) * 2
        minofMTF30 = min(listMeanofMTF30) * 2
        minofMTF50 = min(listMeanofMTF50) * 2
        meanofFourAngleStar_10 = sumofFourAngleStar_10 / (4 * 8) * 2
        meanofFourAngleStar_30 = sumofFourAngleStar_30 / (4 * 8) * 2
        meanofFourAngleStar_50 = sumofFourAngleStar_50 / (4 * 8) * 2

    for card_metric_value_id in card_metric_value_set:
        if card_metric_value_id[2] ==  'MTF 10平均值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 10平均值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                      VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofMTF10))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  'MTF 10最小值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 10最小值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(minofMTF10))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '中心星MTF10(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(中心星MTF10(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofCenterStar_10))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '四角星平均MTF10(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(四角星平均MTF10(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofFourAngleStar_10))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  'MTF 30平均值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 30平均值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofMTF30))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  'MTF 30最小值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 30最小值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(minofMTF30))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '中心星MTF30(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(中心星MTF30(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofCenterStar_30))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '四角星平均MTF30(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(四角星平均MTF30(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofFourAngleStar_30))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  'MTF 50平均值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 50平均值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofMTF50))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  'MTF 50最小值(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(MTF 50最小值(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(minofMTF50))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '中心星MTF50(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(中心星MTF50(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofCenterStar_50))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()

        elif card_metric_value_id[2] ==  '四角星平均MTF50(LW/PH)':
            graphpath = """%s_%s_%s_%s_%s_%s_%s_%s(四角星平均MTF50(LW/PH))""" \
                        %(inf[0], inf[1], inf[2], inf[3], inf[4], inf[5], inf[6], inf[7])
            rating_insert = """INSERT INTO rating_single_te268( lab,graph_path, cellphone_id, light_source_id, card_metric_value_id, distance, result)
                                        VALUES ("%s", "%s", %d, %s, %d, "%s", %f)
                                  """%(lab, graphpath, cellphone_id, light_source_id, int(card_metric_value_id[0]), distance, float(meanofFourAngleStar_50))
            try:
                #print round_robin_insert
                cursor.execute(rating_insert)
                conn.commit()
            except Exception, e:
                print 'repr(e):\t', repr(e)
                conn.rollback()
def classify(list, conn, rootpath):
    card = list[2]
    if card == 'DxO SFR' or card == 'DxO Dot' or card == 'DxO texture':
        handleDxO(list, conn, rootpath)
    elif card == 'TE255' or card == 'grey':
        handleTE255orgrey(list, conn, rootpath)
    elif card == 'Colorchecker':
        handleClolorchecker(list, conn, rootpath)
    elif card == 'TE270':
        handleTE270(list, conn, rootpath)
    elif card == 'Im Dot':
        handleID(list, conn, rootpath)
    elif card == 'TE 268 4to3 A460 H':
        handleTE268(list, conn, rootpath)
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
    rootpath = "/Users/Den1er/Documents/Caict/数据集/4_评分系统数据积累"
    scanFromRoot(rootpath)