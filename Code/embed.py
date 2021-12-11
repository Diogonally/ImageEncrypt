from PIL import Image
from numpy import *
import numpy
from skimage import io
from bitarray import bitarray
from Crypto.Cipher import AES
from Crypto import Random
import base64
import random
import os.path
import sys

base_path = os.path.dirname(os.path.realpath(__file__))  # 获取当前路径
filename = os.path.join(os.path.dirname(base_path), 'server_image',sys.argv[2]+'_encryptImage.png')
E = io.imread(filename) #加密后的图片矩阵
kuan,gao = E.shape #得到宽高像素

K = int(kuan*gao/64) #将图像分割为K块
heng = int(kuan/8) #横着的块数
shu = int(gao/8) #竖着的快数

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

c = e[::8] #提取的K块的最低位平面信息，K个元素，每个元素64bit
# print(len(c)) #4096=K
# print(len(c[0])) #64bit
embedkey = sys.argv[1]
permutationseed = int(embedkey[0:8],16)
#伪随机置换矩阵
# permutationseed = 42
fp = numpy.random.RandomState(permutationseed).permutation(K)
f = list(fp)  #f为伪随机置换
rvf =  [0 for i in range(K)] #rvf为f的逆置换，之后复原有用
for i in range(K):
    rvf[f[i]] = i


cf = [] #c的置换，K个元素，每个元素64bit
for i in range(K):
    cf.append(c[f[i]])
# print(len(cf))#4096=K
# print(len(cf[0]))#64
# print(c[0]) 正确
# print(cf[0]) 正确

u = 2 #预定义参数 暂时设置为2
L = int(K/u) #将cf分成L组
w = 1 

def str2bitarray(msg):  # msg为byte类型字符串 函数功能为将byte转为bit
    msg_2 = ""  # 转为1010拼接成字符串
    for a in msg.encode('utf-8'):    
        a_16 = hex(a)[2:] # ascll 码16进制 str
        a_10 = int("1" + a_16, 16)  # 10进制 int, 防止转二进制最高为0丢失, 所以最高位前加1 , 10进制 int
        a_2 = bin(a_10)[3:] # 二进制 str, 利用ascll码值是8bit, 最前面可以加1,  在切片,去掉
        a_2 = a_2.zfill(8)  # 此时可能不是完整的8位bit，所以前面需要补0
        msg_2 += a_2 
    return bitarray(msg_2)

#需要嵌入的信息
# mstr = "Block cipher based separable reversible data hiding in encrypted images. this system is implemented by djx lyt wxy lq wzh ayswl"
mstr = sys.argv[3]
bitstr = str2bitarray(mstr)
n = L*w - len(bitstr)
m = bitstr
for i in range(n):
    m = m + bitarray("0")

#生成L*w个bit密码
jiamiseed = int(embedkey[8:16],16)
# jiamiseed = 123356789
mimaint = numpy.random.RandomState(jiamiseed).randint(0,2,L*w)
mima = bitarray()
for i in range(L*w):
    mima = mima + str(mimaint[i])

#a为加密好的信息，准备嵌入
a = mima^m #a为L*w bit，加密以后

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
# randonQseed = 123356789
qint = numpy.random.RandomState(randonQseed).randint(0,2,(64*u-w)*w)
for i in range(64*u - w):
    Qi = bitarray()
    for j in range(w):
        Qi += bitarray(str(qint[i*w + j]))
    Q.append(Qi)

H = [] #算法中的H矩阵，64u列，w行，为了方便后续运算，令每列为一个元素，每个元素w个bit
H = I + Q

#对于第l组
def embedding(l,cf,al):
    gl = bitarray() #将cf分成L组后，gl为第l组的信息，有64ubit
    for i in range(u):
        gl += cf[l*u+i] 

    #嵌入信息m L*w bit 2048 第l组嵌入wbit，这里为1bit

    rl = al^gl[0:w] #第l组的a的wbit与g的前wbit异或，得到wbit rl
    rlH = bitarray()
    for i in range(64*u):
        sumi = 0
        for j in range(w):
            sumi += int(rl[j])*int(H[i][j])
        rlH += str(sumi%2)
    # print(rlH)
    vl = gl^rlH #64u bit
    #print(len(vl))#128
    for i in range(u):
        cf[l*u+i] = vl[64*i:64*(i+1)]
    
for l in range(L):
    al = a[w*l:w*(l+1)] #将a分成l组
    embedding(l,cf,al) #嵌入到cf中

rvcf = [] #cf的置换，K个元素，每个元素64bit
for i in range(K):
    rvcf.append(cf[rvf[i]]) #将之前置换出去的c置换回来

for i in range(K):
    e[i*8] = rvcf[i] #将原加密图像的信息替换掉


def getEi(i,ei,Ee):#根据第i块的信息得到第i块
    for r in range(8):
        for s in range(8):
            for k in range(8):
                Ee[(i%heng)*8+r,int(i/shu)*8+s] += int(ei[k][r*8+s])*(2**k)

ei = []
Ee = uint8(zeros(E.shape))#加密后的图片矩阵

for i in range(K):
    ei = e[8*i:8*(i+1)]
    getEi(i,ei,Ee)


filename1 = os.path.join(os.path.dirname(base_path), 'server_image',sys.argv[2]+'_embedImage.png')
io.imsave(filename1,Ee)
