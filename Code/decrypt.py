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
filename = os.path.join(os.path.dirname(base_path), 'receiver_image',sys.argv[2]+'_embedImage.png')
E = io.imread(filename) #解密前的图片矩阵
kuan,gao = E.shape #得到宽高像素

K = int(kuan*gao/64) #将图像分割为K块
heng = int(kuan/8) #横着的块数
shu = int(gao/8) #竖着的快数

P = uint8(zeros(E.shape))#加密后的图片矩阵

def getei(i): #获取第i块的全部信息
    ei = [] #第i个块的信息 512bit 有8个元素，每个元素有64bit
    for k in range(8):
        eik = bitarray() #第k个bit平面 64bit
        for r in range(8):#第（r,s）个像素
            for s in range(8):
                eirsk = (E[(i%heng)*8+r,int(i/shu)*8+s]>>k)%2
                eik.append(eirsk)
        ei.append(eik)
    return ei

def str2bitarray(msg):  # msg为byte类型字符串 函数功能为将byte转为bit
    msg_2 = ""  # 转为1010拼接成字符串
    for a in msg:    
        a_16 = hex(a)[2:] # ascll 码16进制 str
        a_10 = int("1" + a_16, 16)  # 10进制 int, 防止转二进制最高为0丢失, 所以最高位前加1 , 10进制 int
        a_2 = bin(a_10)[3:] # 二进制 str, 利用ascll码值是8bit, 最前面可以加1,  在切片,去掉
        a_2 = a_2.zfill(8)  # 此时可能不是完整的8位bit，所以前面需要补0
        msg_2 += a_2 
    return bitarray(msg_2)

def getPi(i,bi,P):#根据第i块的信息得到第i块
    for r in range(8):
        for s in range(8):
            for k in range(8):
                P[(i%heng)*8+r,int(i/shu)*8+s] += int(bi[k][r*8+s])*(2**k)

e = [] #全部图像的信息512K bit 8K个元素，每个元素有64bit

s = [] #解密前的数组，有4K*128bit

for i in range(K):
    e += getei(i) #8K个元素，每个元素有64bit

for i in range(4*K):
    s += (e[2*i] + e[2*i+1])

sbit = bitarray(s)
sstr = sbit.tobytes()#密文转成byte类型
# print(S[0])

#解密算法
key = sys.argv[1]
iv = "1234567812345678"
cipher = AES.new(key,AES.MODE_CBC,iv)
bstr = cipher.decrypt(sstr) #解密以后的明文，为byte类型

bbit = str2bitarray(bstr) #将密文转为bit类型，有128*4K bit
b = [] #8K个元素，每个元素有64bit

for i in range(8*K):
    b.append(bbit[64*i:64*(i+1)])

bi = []

for i in range(K):
    bi = b[8*i:8*(i+1)]
    getPi(i,bi,P)


filename1 = os.path.join(os.path.dirname(base_path), 'receiver_image', sys.argv[2]+'_decryptImage.png')
io.imsave(filename1,P)