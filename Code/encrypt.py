from PIL import Image
from numpy import *
from skimage import io
from bitarray import bitarray
from Crypto.Cipher import AES
from Crypto import Random
import base64
import os.path
import sys

base_path = os.path.dirname(os.path.realpath(__file__))  # 获取当前路径
#filename = os.path.join(base_path, sys.argv[2]+'_originalImage.png')
filename = os.path.join(os.path.dirname(base_path), 'sender_image',sys.argv[2]+'_originalImage.png')
#filename2 = os.path.join(base_path, sys.argv[2]+'_originalImage_convert.png')
filename2 = os.path.join(os.path.dirname(base_path), 'sender_image',sys.argv[2]+'_originalImage_convert.png')
image_1 = Image.open(filename)
image = image_1.convert('L')
image.save(filename2)

O = io.imread(filename2) #加密前的图片矩阵
kuan,gao = O.shape #得到宽高像素

K = int(kuan*gao/64) #将图像分割为K块
heng = int(kuan/8) #横着的块数
shu = int(gao/8) #竖着的快数

E = uint8(zeros(O.shape))#加密后的图片矩阵

def getbi(i): #获取第i块的全部信息
    bi = [] #第i个块的信息 512bit 有8个元素，每个元素有64bit
    for k in range(8):
        bik = bitarray() #第k个bit平面 64bit
        for r in range(8):#第（r,s）个像素
            for s in range(8):
                birsk = (O[(i%heng)*8+r,int(i/shu)*8+s]>>k)%2
                bik.append(birsk)
        bi.append(bik)
    return bi

def str2bitarray(msg):  # msg为byte类型字符串 函数功能为将byte转为bit
    msg_2 = ""  # 转为1010拼接成字符串
    for a in msg:    
        a_16 = hex(a)[2:] # ascll 码16进制 str
        a_10 = int("1" + a_16, 16)  # 10进制 int, 防止转二进制最高为0丢失, 所以最高位前加1 , 10进制 int
        a_2 = bin(a_10)[3:] # 二进制 str, 利用ascll码值是8bit, 最前面可以加1,  在切片,去掉
        a_2 = a_2.zfill(8)  # 此时可能不是完整的8位bit，所以前面需要补0
        msg_2 += a_2 
    return bitarray(msg_2)


def getEi(i,ci,E):#根据第i块的信息得到第i块
    for r in range(8):
        for s in range(8):
            for k in range(8):
                E[(i%heng)*8+r,int(i/shu)*8+s] += int(ci[k][r*8+s])*(2**k)


b = [] #全部图像的信息512K bit 8K个元素，每个元素有64bit

s = [] #加密前的数组，有4K*128bit

for i in range(K):
    b += getbi(i) #8K个元素，每个元素有64bit

for i in range(4*K):
    s += (b[2*i] + b[2*i+1])

sbit = bitarray(s)
sstr = sbit.tobytes()#明文转成byte类型
# print(len(sbit))
# print(len(sstr))

#加密算法
key = sys.argv[1]
iv = "1234567812345678"
cipher = AES.new(key,AES.MODE_CBC,iv)
estr = cipher.encrypt(sstr) #加密后的密文，为byte类型
# print(len(estr))

ebit = str2bitarray(estr) #将密文转为bit类型，有128*4K bit
e = [] #8K个元素，每个元素有64bit
# print(len(ebit))

for i in range(8*K):
    e.append(ebit[64*i:64*(i+1)])

ci = []

for i in range(K):
    ci = e[8*i:8*(i+1)]
    getEi(i,ci,E)

filename = os.path.join(os.path.dirname(base_path), 'sender_image',sys.argv[2]+'_encryptImage.png')
io.imsave(filename,E)