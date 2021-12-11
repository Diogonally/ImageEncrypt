from PIL import Image
from numpy import *
import numpy
from skimage import io
from bitarray import bitarray
from Crypto.Cipher import AES
from Crypto import Random
import base64
import os.path
import random
import sys

base_path = os.path.dirname(os.path.realpath(__file__))  # 获取当前路径
filename = os.path.join(os.path.dirname(base_path), 'receiver_image', sys.argv[3]+'_embedImage.png')
E = io.imread(filename) #加密后的图片矩阵
kuan,gao = E.shape #得到宽高像素

K = int(kuan*gao/64) #将图像分割为K块
heng = int(kuan/8) #横着的块数
shu = int(gao/8) #竖着的块数

def getci(i): #获取第i块的全部信息
    ci = [] #第i个块的信息 512bit 有8个元素，每个元素有64bit
    for k in range(8):
        cik = bitarray() #第k个bit平面 64bit
        for r in range(8):#第（r,s）个像素
            for s in range(8):
                cirsk = (E[(i%heng)*8+r,int(i/shu)*8+s]>>k)%2
                cik.append(cirsk)
        ci.append(cik)
    return ci

e = [] #全部图像的信息512K bit 8K个元素，每个元素有64bit

for i in range(K):
    e += getci(i) #8K个元素，每个元素有64bit

# c = e[::8] #提取的K块的最低位平面信息，K个元素，每个元素64bit

embedkey = sys.argv[2]
permutationseed = int(embedkey[0:8],16)
#伪随机置换矩阵
# permutationseed = 42
fp = numpy.random.RandomState(permutationseed).permutation(K)
f = list(fp)  #f为伪随机置换
rvf =  [0 for i in range(K)] #rvf为f的逆置换，之后复原有用
for i in range(K):
    rvf[f[i]] = i

# cf = [] #c的置换，K个元素，每个元素64bit
# for i in range(K):
#     cf.append(c[f[i]])

c8 = [] #K个元素，每个元素为64*8bit，为一个块的8个位平面
for i in range(K):
    c8.append(e[8*i:8*(i+1)])
# print(len(c8)) #4096=K
# print(len(c8[0])) #8

cf8 = [] #c8的置换，K个元素，每个元素为8个元素的向量，八个元素每个元素为64bit
for i in range(K):
    cf8.append(c8[f[i]])

cf = [] #置换后，提取的最低位平面，K个元素，每个元素64bit
for i in range(K):
    cf.append(cf8[i][0])

u = 2
L = int(K/u)
w = 1

#需要提取的信息###
#对于第l组
def extract1(l,cf,w): 
    gl = bitarray() #将cf分成L组后，gl为第l组的信息，有64ubit
    for i in range(u):
        gl += cf[l*u+i]
    #print(len(gl))  #128
    al = gl[0:w]
    return al
 
a = bitarray()
for l in range(L):
   a += extract1(l,cf,w)
 
# print(a)
#生成L*w个bit密码mima
jiamiseed = int(embedkey[8:16],16)
mimaint = numpy.random.RandomState(jiamiseed).randint(0,2,L*w)
mima = bitarray()
for i in range(L*w):
    mima = mima + str(mimaint[i])

#a为加密好的信息，准备提取
m = mima^a #a为L*w bit，加密以后

'''
def bitarray2str(bitarray_obj):
    return bitarray_obj.tostring()
'''
def bitarray2str(bit):
    return bit.tobytes().decode('utf-8')

print(bitarray2str(m))

#生成n位比特串全部可能td
T = []#T中存储了每种td的可能，td有wbit，从而有2^w个元素，每个元素wbit
A = [0 for i in range(w)]
def binary(n):
    if(n < 1):
        tbit = bitarray()
        for i in range(w):
            tbit += str(A[i])
        T.append(tbit)  #Assume A is a global variable
    else:
        A[n-1] = 0
        binary(n-1)
        A[n-1] = 1
        binary(n-1)
binary(w)

# 矩阵H的生成
I = []
for i in range(w):
    Ii = bitarray()
    for j in range(w):
        if i == j:
            Ii += bitarray("1")
        else:
            Ii += bitarray("0")
    I.append(Ii)

Q = [] #为一个随机01阵
randonQseed = int(embedkey[4:12],16)
qint = numpy.random.RandomState(randonQseed).randint(0,2,(64*u-w)*w)
for i in range(64*u - w):
    Qi = bitarray()
    for j in range(w):
        Qi += bitarray(str(qint[i*w + j]))
    Q.append(Qi)

H = [] #算法中的H矩阵，64u列，w行，为了方便后续运算，令每列为一个元素，每个元素w个bit
H = I + Q

#以下是循环：对于每个l，有2^w种可能的tj

def byte2bitarray(msg):  # msg为byte类型字符串 函数功能为将byte转为bit
    msg_2 = ""  # 转为1010拼接成字符串
    for a in msg:    
        a_16 = hex(a)[2:] # ascll 码16进制 str
        a_10 = int("1" + a_16, 16)  # 10进制 int, 防止转二进制最高为0丢失, 所以最高位前加1 , 10进制 int
        a_2 = bin(a_10)[3:] # 二进制 str, 利用ascll码值是8bit, 最前面可以加1,  在切片,去掉
        a_2 = a_2.zfill(8)  # 此时可能不是完整的8位bit，所以前面需要补0
        msg_2 += a_2 
    return bitarray(msg_2)

def trytd(td,gl,al,l): #对于第l组，尝试第d中可能，并计算sum
    tdal = td^al
    taH = bitarray()
    for i in range(64*u):
        sumi = 0
        for j in range(w):
            sumi += int(tdal[j])*int(H[i][j])
        taH += str(sumi%2)
    wdl = taH^gl #64ubit 

    pf8lu = [] #u个元素，每个元素为含8个的元素的元素，每个元素有64bit
    for i in range(u):#对第l组中的每个cf块进行解密，构造Pf
        cf8[l*u+i][0] = wdl[64*i:64*(i+1)] #将第l组gl换成wl（换的是最低位平面的64bit）
        if(f[l*u+i]==0):
            IV = "1234567812345678"
        else:
            IVbit = c8[f[l*u+i]-1][6]+c8[f[l*u+i]-1][7]
            # print(IVbit)
            IV = IVbit.tobytes()
        key = sys.argv[1]
        cf8lui = bitarray()
        # print("u = ",i," l = 0 ","IV:",IV)
        for j in range(8):
            cf8lui += cf8[l*u+i][j]
        cf8lui_str = cf8lui.tobytes()
        cipher = AES.new(key,AES.MODE_CBC,IV)
        pstr = cipher.decrypt(cf8lui_str) #解密以后的明文，为byte类型
        pbit = byte2bitarray(pstr) #512bit
        pf8lui = []
        for j in range(8):
            pf8lui.append(pbit[64*j:64*(j+1)])
        pf8lu.append(pf8lui) 

    Pflu = []#存储了从cf8的l*u到l*u+u-1转成的原图块信息，总共u个元素，每个元素为一个8*8的块
    for i in range(u):
        Pflui = zeros((8,8),dtype = "uint8")
        Pflu.append(Pflui)
    #构建Pflu
    for i in range(u):
        for r in range(8):
            for s in range(8):
                for k in range(8):
                    Pflu[i][r,s] += int(pf8lu[i][k][r*8+s])*(2**k)
        # print(Pflu[i])
    #计算此次尝试的目标函数
    try_sum = 0
    for i in range(u):
        sum1 = 0
        sum2 = 0
        for p in range(1,8):
            for q in range(8):
                if(Pflu[i][p,q]>Pflu[i][p-1,q]):
                    sum1 += (Pflu[i][p,q]-Pflu[i][p-1,q])
                else:
                    sum1 += (Pflu[i][p-1,q]-Pflu[i][p,q])
        for p in range(8):
            for q in range(1,8):
                if(Pflu[i][p,q]>Pflu[i][p,q-1]):
                    sum2 += (Pflu[i][p,q]-Pflu[i][p,q-1])
                else:
                    sum2 += (Pflu[i][p,q-1]-Pflu[i][p,q])
        try_sum += (sum1 + sum2)
    return try_sum

for l in range(L):
    gl = bitarray()
    for i in range(u):
        gl += cf[l*u+i]  #将cf分成L组后，gl为第l组的信息，有64ubit
    al = a[w*l:w*(l+1)]
    minsum = 10000000000
    mind = 0 #表示对于第l组，最后猜测正确的第d种可能
    for d in range(len(T)):
        td = T[d]
        tsum = trytd(td,gl,al,l)
        trytd(td,gl,al,l)
        if(tsum < minsum):
            minsum = tsum
            mind = d
    mint = T[mind]#最终第d个尝试为目标函数最小的参数，从而得到了猜测的td
    tdal = mint^al
    tdalH = bitarray()
    for i in range(64*u):
        sumi = 0
        for j in range(w):
            sumi += int(tdal[j])*int(H[i][j])
        tdalH += str(sumi%2)
    wmindl = tdalH^gl
    for i in range(u):
        cf[l*u+i] = wmindl[64*i:64*(i+1)]

rvcf = [] #cf的置换，K个元素，每个元素64bit
for i in range(K):
    rvcf.append(cf[rvf[i]]) #将之前置换出去的c置换回来

for i in range(K):
    e[i*8] = rvcf[i] #将原加密图像的信息替换掉

s = [] #解密前的数组，有4K*128bit

for i in range(4*K):
    s += (e[2*i] + e[2*i+1])

sbit = bitarray(s)
sstr = sbit.tobytes()#密文转成byte类型
# print(S[0])

#解密算法
key = sys.argv[1]
iv = "1234567812345678"
cipher2 = AES.new(key,AES.MODE_CBC,iv)
bstr = cipher2.decrypt(sstr) #解密以后的明文，为byte类型

bbit = byte2bitarray(bstr) #将密文转为bit类型，有128*4K bit
b = [] #8K个元素，每个元素有64bit

for i in range(8*K):
    b.append(bbit[64*i:64*(i+1)])

bi = []

P = uint8(zeros(E.shape))#加密后的图片矩阵

def getPi(i,bi,P):#根据第i块的信息得到第i块
    for r in range(8):
        for s in range(8):
            for k in range(8):
                P[(i%heng)*8+r,int(i/shu)*8+s] += int(bi[k][r*8+s])*(2**k)

for i in range(K):
    bi = b[8*i:8*(i+1)]
    getPi(i,bi,P)

filename1 = os.path.join(os.path.dirname(base_path), 'receiver_image',sys.argv[3]+'_huifuImage.png')
io.imsave(filename1,P)
