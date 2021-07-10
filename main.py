# -*- coding: utf-8 -*-
"""Final_teamSCI_구본정김지은이혜승.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1e7i7RwFOoYQkb2kvGb-z_ndoJF9LDiVh
"""

import torch
import os
import torchvision
import torchvision.transforms as transforms
from torchvision.datasets import ImageFolder
import matplotlib.pyplot as plt
import cv2
from torchvision.utils import save_image
import numpy as np
import torch.nn as nn
import torch.optim as optim
import torch.nn.init as init
import torchvision.datasets as dset
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
from torch.autograd import Variable
from sklearn.metrics import f1_score, accuracy_score
from sklearn.metrics import confusion_matrix
import seaborn as sns;sns.set()
from torchsummary import summary

torch.manual_seed(0)

!pip install livelossplot
from livelossplot import PlotLosses

from google.colab import drive
drive.mount('/content/drive')

"""## step1: train : val : test split

*  nodefect(정상 데이터) - 6 : 2 : 2 ( 85, 28, 28장 )
*  defect(결함 데이터) - 0 : 1 : 1 ( 0, 52, 53장 )
"""

# data load
transform = transforms.Compose([transforms.ToTensor()])

nodefect_dataset = ImageFolder(root= "/content/drive/Shared drives/data/data/NODefect/", transform=transform)
nodefect_loader = torch.utils.data.DataLoader(nodefect_dataset)

# nodefect data load
## train : val : test = 6 : 2 : 2 로 split
train_size = int(0.6 * len(nodefect_dataset) +1) # 85
val_size = int(0.2 * len(nodefect_dataset)) # 28
test_size = len(nodefect_dataset) - train_size - val_size # 28
print(train_size, val_size, test_size)

train_dataset_split, val_dataset_split, test_dataset_split = torch.utils.data.random_split(nodefect_dataset, [train_size, val_size, test_size])

# defect data load
# 0094_027_05.png 이미지 사이즈 오류 -> 삭제했음
transform = transforms.Compose([transforms.ToTensor()])

defect_dataset = ImageFolder(root= "/content/drive/Shared drives/data/data/Defect/", transform=transform)
defect_loader = torch.utils.data.DataLoader(defect_dataset)
## train : val : test = 0 : 1 : 1 로 split
val_size = int(0.5 * len(defect_dataset)) # 52
test_size = len(defect_dataset) - val_size # 53
print( val_size, test_size)

val_dataset_split2, test_dataset_split2 = torch.utils.data.random_split(defect_dataset, [val_size, test_size])

train_split_loader = torch.utils.data.DataLoader(train_dataset_split)

val_nodefectsplit_loader = torch.utils.data.DataLoader(val_dataset_split)
val_defectsplit_loader = torch.utils.data.DataLoader(val_dataset_split2)

test_nodefectsplit_loader = torch.utils.data.DataLoader(test_dataset_split)
test_defectsplit_loader = torch.utils.data.DataLoader(test_dataset_split2)

"""## step2: divided into patches

#### dataloader로 불러온 이미지를 gdrive에 **_nodefect(or defect).png 형태로 저장
"""

def save_img(img, idx, targets, path, defectness):  
  if defectness == True: # defect 이미지일때
    save_path = os.path.join(path,"{0:02d}_defect.png".format(idx+28))
    print("{0:02d}_defect.png".format(idx+28))
  else: # nodefect 이미지일때
    save_path = os.path.join(path,"{0:02d}_nodefect.png".format(idx))
    print("{0:02d}_nodefect.png".format(idx))


  save_image(img, save_path)   #자른 이미지 저장

def process(path, defectness, loader):
  for batch_idx, (inputs, targets) in enumerate(loader):
    save_img(inputs[0], batch_idx, targets, path,defectness)

# train
process("/content/drive/Shared drives/data/nocrop/train", False, train_split_loader)

# test - nodefect (# = 28)
process("/content/drive/Shared drives/data/nocrop/test", False, test_nodefectsplit_loader)

# test - defect (# = 53)
process("/content/drive/Shared drives/data/nocrop/test", True, test_defectsplit_loader)

# val - nodefect ( # = 28)
process("/content/drive/Shared drives/data/nocrop/val", False, val_nodefectsplit_loader)
process("/content/drive/Shared drives/data/nocrop//val_for_training", False, val_nodefectsplit_loader)

# val - defect (# = 52)
process("/content/drive/Shared drives/data/nocrop/val", True, val_defectsplit_loader)

"""#### train, val_for_training(only nodefect) 이미지들을 패치로 쪼개서 tensor형태로 저장

- test, validation set은 test/validation 함수 내에서 patch화 할것이므로 전처리 단계에서는 제외한다.
"""

import torch
from torchvision import transforms
import matplotlib.pyplot as plt
from PIL import Image
import cv2
import glob

### 저장되어있는 모든 crop된 이미지들 불러오기(grayscale로) - images list에 저장
train_images = [cv2.imread(file, cv2.IMREAD_GRAYSCALE) for file in glob.glob("/content/drive/Shared drives/data/nocrop/train/*.png")]
print(train_images[0].shape)

val_for_training_images = [cv2.imread(file, cv2.IMREAD_GRAYSCALE) for file in glob.glob("/content/drive/Shared drives/data/nocrop/val_for_training/*.png")]
print(val_for_training_images[0].shape)

print(len(train_images)) # 85개
print(train_images[0].shape) # 256,2096

print(len(val_for_training_images)) # 28개
print(val_for_training_images[0].shape) # 256,2096

""" 
patch로 쪼개주는 함수
: image list를 받아서, tensor로 변환 
-> .view(패치개수, 패치사이즈, 패치사이즈)
-> train_patches.shape = 85 256 64 64 / val_for_training_patches.shape = 28 256 64 64
"""
def patch(images):
  patch_size = 64
  for i in range(len(images)):
    images[i] = transforms.ToTensor()((images[i]))
    # unfold로 shape조절 --> view --> [patch개수, patch_size, patch_size]
    patches = images[i].data.unfold(1, patch_size, patch_size).unfold(2, patch_size, patch_size) 
    patches = patches.contiguous().view(-1, patch_size, patch_size) 
    #print(patches.shape)
    if i == 0:
      patch = patches
    if i > 0:
      patches = torch.cat((patch, patches))
      patch = patches
  # print(patches.shape)

  patches = patches.view(len(images), -1, patch_size, patch_size) 
  return patches

"""
patch를 이미지로 gdrive에 저장해주는 함수
: patches텐서를 이미지번호 폴더에, 각 256개의 패치를 저장
"""
def save_patches(patches, set):
  import os
  patch_path="/content/drive/Shared drives/data/nocrop/patch"
  if not os.path.isdir( patch_path ) :
    os.mkdir( patch_path )

  # cv2.imwrite사용하기 위해 patches를 numpy로 변환
  patches = patches.numpy()

  for i in range(1, patches.shape[0]+1): # original image 1 ~ 85번(폴더구분)
    for num in range(1, patches.shape[1]+1): # patch 정보는 파일이름에 저장
          path = os.path.join("/content/drive/Shared drives/data/nocrop/patch", set, "image{0:02d}".format(i))
          if not os.path.isdir( path ) :
            os.mkdir( path )
          filename = "{0:03d}.png".format(num)
          print(path + "/" + filename)
          # image로 저장해서 다시 로드해오려고함
          # 이미지로저장하기위해 다시 *255
          cv2.imwrite(path + "/" + filename, patches[i-1,num-1,:]*255.0) 
  print("Saving pathces complete!")

train_patches = patch(train_images)
print(train_patches.shape) # 85 256 64 64 # 사이즈=64*64;이미지당 패치개수=256

val_for_training_patches = patch(val_for_training_images)
print(val_for_training_patches.shape) # 28 256 64 64

save_patches(train_patches, "train")

save_patches(val_for_training_patches, "val_for_training")

"""## step3: Auto encoder
1. Autoencoder1 with Linear dimension reduction
- layer 5개
- INPUT - linear - **H1** - linear - *H2(latent)* -  linear - **H3** - OUTPUT

2. Autoencoder2 with nonlinear(PReLU) dimension reduction
- layer 7개
- INPUT - linear - PReLU - **H1** - linear -  PReLU - **H2** -  linear - **H3(latent)** - linear - **H4** -  PReLU - linear - **H5** -  PReLU - linear - OUTPUT

3. Autoencoder3 based on deep CNN with tanh

4. Autoencoder4 based on deep CNN with sigmoid
- decoding의 마지막 activation function만 변경

### training 준비
"""

# hyperparameter
batch_size = 20

transform = transforms.Compose([transforms.Grayscale(num_output_channels=1),
                                transforms.ToTensor()])

patch_train_dataset = ImageFolder(root= "/content/drive/Shared drives/data/nocrop/patch/train", transform=transform)
patch_train_loader = torch.utils.data.DataLoader(patch_train_dataset, shuffle=False, batch_size=batch_size)

# validation data for training(only nodefect)
patch_val_dataset = ImageFolder(root= "/content/drive/Shared drives/data/nocrop/patch/val_for_training", transform=transform)
patch_val_loader = torch.utils.data.DataLoader(patch_val_dataset,  shuffle=False, batch_size=batch_size)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)

"""### modeling"""

class Autoencoder1(nn.Module):
    def __init__(self):
        super(Autoencoder1,self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(64*64, 1000),
            nn.Linear(1000, 10)
        )
        self.decoder = nn.Sequential(
            nn.Linear(10, 1000),
            nn.Linear(1000, 64*64) 
        )        
    def forward(self,x):
        x = x.view(x.size(0), -1)
        encoded = self.encoder(x)
        out = self.decoder(encoded).view(x.size(0), 1, 64, 64)
        return out

model1 = Autoencoder1().to(device)

print(Autoencoder1().cuda())

class Autoencoder2(nn.Module):
    def __init__(self):
        super(Autoencoder2,self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(64*64, 32*32),
            nn.PReLU(32*32),
            nn.Linear(32*32, 16*16),
            nn.PReLU(16*16),
            nn.Linear(16*16,4)
        )
        self.decoder = nn.Sequential(
            nn.Linear(4, 16*16),
            nn.PReLU(16*16),
            nn.Linear(16*16, 32*32),
            nn.PReLU(32*32),
            nn.Linear(32*32, 64*64)
        )   
                
    def forward(self,x):
        x = x.view(x.size(0), -1)
        encoded = self.encoder(x)
       # out = self.decoder(encoded)
        out = self.decoder(encoded).view(x.size(0), 1, 64, 64)
        return out

model2 = Autoencoder2().to(device)

print(Autoencoder2().cuda())

class Autoencoder3(nn.Module):
    def __init__(self):
        super(Autoencoder3,self).__init__()
        self.encoder = nn.Sequential (
          # conv 1
          nn.Conv2d(in_channels= 1, out_channels=16, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # # conv 2
          nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 3
          nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(64),

          # # conv 4
          nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(128),

          # # conv 5
          nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(256)
        )

        self.decoder = nn.Sequential (
          # # conv 6
          nn.ConvTranspose2d(in_channels=256, out_channels=128, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(128),

          # # conv 7
          nn.ConvTranspose2d(in_channels=128, out_channels=64, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(64),

          # # conv 8
          nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 9
          nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # conv 10
          nn.ConvTranspose2d(in_channels=16, out_channels=1, kernel_size=3, stride=1, padding=1),
          nn.Tanh()
        )

    def forward(self, x):
      encoded = self.encoder(x)
      out = self.decoder(encoded).view(x.size(0), 1, 64, 64)
      return out

model3 = Autoencoder3().to(device)

summary(model3,(1,64,64))

print(Autoencoder3().cuda())

class Autoencoder4(nn.Module):
    def __init__(self):
        super(Autoencoder4,self).__init__()
        self.encoder = nn.Sequential (
          # conv 1
          nn.Conv2d(in_channels= 1, out_channels=16, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # # conv 2
          nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 3
          nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(64),

          # # conv 4
          nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(128),

          # # conv 5
          nn.Conv2d(in_channels=128, out_channels=256, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(256)
        )

        self.decoder = nn.Sequential (
          # # conv 6
          nn.ConvTranspose2d(in_channels=256, out_channels=128, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(128),

          # # conv 7
          nn.ConvTranspose2d(in_channels=128, out_channels=64, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(64),

          # # conv 8
          nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 9
          nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=3, stride=1, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # conv 10
          nn.ConvTranspose2d(in_channels=16, out_channels=1, kernel_size=3, stride=1, padding=1),
          nn.Sigmoid()
        )

    def forward(self, x):
      encoded = self.encoder(x)
      out = self.decoder(encoded).view(x.size(0), 1, 64, 64)
      return out

model4 = Autoencoder4().to(device)

summary(model4,(1,64,64))

# from IPython.display import Image
# from google.colab import files

# files.upload()

# Image('model5_architecture.png')

## model 3,4 와 다르게 stride를 1 대신 3과 2로 설정하여 시도해보았다.
## 결과적으로는 이미지 재구성력이 떨어지므로
## 휴리스틱한 방법으로 모델 채택하지 않음
class Autoencoder5(nn.Module):
    def __init__(self):
        super(Autoencoder5,self).__init__()
        self.encoder = nn.Sequential (
          # conv 1
          nn.Conv2d(in_channels= 1, out_channels=16, kernel_size=3, stride=3, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # # conv 2
          nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=3, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 3
          nn.Conv2d(in_channels=32, out_channels=64, kernel_size=2, stride=2, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(64)
        )

        self.decoder = nn.Sequential (
          # # conv 4
          nn.ConvTranspose2d(in_channels=64, out_channels=32, kernel_size=2, stride=2, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(32),

          # # conv 5
          nn.ConvTranspose2d(in_channels=32, out_channels=16, kernel_size=3, stride=3, padding=1),
          nn.PReLU(),
          nn.BatchNorm2d(16),

          # conv 5
          nn.ConvTranspose2d(in_channels=16, out_channels=1, kernel_size=3, stride=3, padding=1),
          nn.Sigmoid()
        )

    def forward(self, x):
      encoded = self.encoder(x)
      out = self.decoder(encoded).view(x.size(0), 1, 64, 64)
      return out

model5 = Autoencoder5().to(device)

summary(model5,(1,64,64))

"""### training
- autoencoder1, 2, 3, 4 모델을 gdrive에 .pth형태로 save.
"""

def train(model, patch_train_loader, patch_val_loader, EPOCHS, learning_rate):
  loss_func = nn.MSELoss()
  optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)#, weight_decay=0.99)
  liveloss = PlotLosses()
  lr2_tr_loss = []
  lr2_val_loss = []
  model_losses, valid_losses = [], []
      
  for epoch in range(EPOCHS):
    print("epoch{}".format(epoch))
    model_losses, valid_losses = [], []
    logs = {}
    prefix = ''
      
    # with train data
    model.train()
    for idx, (data,target) in enumerate(patch_train_loader):
        data = torch.autograd.Variable(data).to(device = device, dtype = torch.float)
        print(data.shape)
        optimizer.zero_grad()
        pred = model(data)
        print(pred.shape)
        loss = loss_func(pred, data)
        # Backpropagation
        loss.backward()
        # update
        optimizer.step()
        # loss save
        model_losses.append(loss.cpu().data.item())
        logs[prefix + 'MSE loss'] = loss.item()
        print(idx,"complete")
          
    ## with validation data(only nodefect)
    model.eval()
    for idx, (data,target) in enumerate(patch_val_loader):
        data = torch.autograd.Variable(data).to(device = device, dtype = torch.float)
        pred = model(data)
        loss = loss_func(pred, data)
        valid_losses.append(loss.item())
        prefix = 'val_'
        logs[prefix + 'MSE loss'] = loss.item()
             
    lr2_tr_loss.append(np.mean(model_losses))
    lr2_val_loss.append(np.mean(valid_losses))
    liveloss.update(logs)
    liveloss.draw()
    print ("Epoch:", epoch+1, " Training Loss: ", np.mean(model_losses), " Valid Loss: ", np.mean(valid_losses))
    ## epoch 별로 모델을 저장을 해서, 혹시 overfitting이 된다면 그 이전의 epoch때를 저장해서 AE모델로 사용하고자한다.
    path = os.path.join("/content/drive/Shared drives/data/nocrop/model/hs/model{}".format(str(model)[11:12]),str(model)[:12] + '_epoch{}.pth'.format(epoch))
    torch.save(model.state_dict(), path)
    
    ## epoch19(즉 마지막 에포크)때의 모델을 AE모델로 저장
    if epoch == EPOCHS -1:
        path = os.path.join("/content/drive/Shared drives/data/nocrop/model/hs",str(model)[:12] + '.pth')
        torch.save(model.state_dict(), path)
        return lr2_tr_loss, lr2_val_loss

"""AE model1

"""

EPOCHS = 20
learning_rate = 1e-3
train_loss1,val_loss1 = train(model1, patch_train_loader, patch_val_loader, EPOCHS, learning_rate)

print(train_loss1)
print(val_loss1)

"""AE model2"""

EPOCHS = 20
learning_rate = 1e-3
train_loss2, val_loss2 = train(model2, patch_train_loader, patch_val_loader, EPOCHS, learning_rate)

print(train_loss2)
print(val_loss2)

"""AE model3"""

EPOCHS = 20
learning_rate = 1e-3 # 1e-3 ~ 1e-4
train_loss3 ,val_loss3 = train(model3, patch_train_loader, patch_val_loader, EPOCHS, learning_rate)

print(train_loss4)
print(val_loss4)

"""AE model4"""

EPOCHS = 20
learning_rate = 1e-4 # 1e-3 ~ 1e-4
train_loss4, val_loss4 = train(model4, patch_train_loader, patch_val_loader, EPOCHS, learning_rate)

print(train_loss4)
print(val_loss4)

"""AE model5"""

# EPOCHS = 20
# learning_rate = 1e-4 
# train_loss5, val_loss5 = train(model5, patch_train_loader, patch_val_loader, EPOCHS, learning_rate)

# print(train_loss5)
# print(val_loss5)

"""## step4: validation

#### validation imageset --> patch
"""

### validation set for validation
import glob
import cv2
validation_images = [cv2.imread(file, cv2.IMREAD_GRAYSCALE) for file in sorted(glob.glob("/content/drive/Shared drives/data/nocrop/val/*.png"))]
print(validation_images[0].shape)
print(len(validation_images))

## validation 이미지(정상28, 결함52--> 총 80개)를 patch tensor로 만들어줌
## validation_patches: 80, 256, 64, 64
validation_patches = patch(validation_images)

"""#### original image & reconstructed images visualization

"""

"""
AE based on CNN 모델이 제대로 패치 이미지를 reconstruct하는지 확인하기 위해
visualization하는 코드
"""
def visualization(model_num, validation_patches):
  device = 'cpu'
  ## model load
  models = [Autoencoder1().to(device), Autoencoder2().to(device), 
            Autoencoder3().to(device), Autoencoder4().to(device)]
  new_model= models[model_num-1]
  new_model.load_state_dict(torch.load("/content/drive/Shared drives/data/nocrop/model/hs/model{}/Autoencoder{}_epoch19.pth".format(model_num,model_num)))
  
  new_model.eval()

  img_idx = 0
  ## 한 이미지에 들어있는 patch들을 매 loop마다 불러온다. 
  ## 즉, 256개의 패치를 256, 64, 64 사이즈의 텐서로 불러온다.
  for patch in validation_patches:
    if img_idx < 53:
      img_idx += 1 
      continue
    # 예시로 defect 이미지 하나에 대한 patch들을 출력한다.
    elif img_idx == 53:
      ## 각 패치를 매 loop마다 불러온다.
      for patch_idx in range(256):
        original = patch[patch_idx].view(1,1,64,64)
        original = Variable(original).cpu()

        pred = new_model(original)
        pred = pred.view(64, 64).detach()

        ## original 패치 이미지 출력
        plt.subplot(1,2,1)
        plt.title("Original")
        plt.imshow(np.transpose(original.view(64,64), (0,1))*255.,cmap='gray', vmin=0, vmax=255)
        ## reconstructed 패치 이미지 출력
        plt.subplot(1,2,2)
        plt.title("Reconstructed")
        plt.imshow(np.transpose(pred,(0,1))*255.,cmap='gray', vmin=0, vmax=255)
        plt.show()
        img_idx += 1
    else:
      break

# patch로 잘라내기 이전의 원본 이미지
plt.imshow(validation_images[53].view(256,4096), cmap='gray')

# model1
# Input original image -> AE -> Reconstructed image
visualization(1, validation_patches)

# model2
# Input original image -> AE -> Reconstructed image
visualization(2, validation_patches)

# model3
# Input original image -> AE -> Reconstructed image
visualization(3, validation_patches)

# model4
# Input original image -> AE -> Reconstructed image
visualization(4, validation_patches)

# # model5 # cnn stride를 키웠을 때 재구성이 잘 되지않음. --> 모델 채택 x
# # Input original image -> AE -> Reconstructed image
# visualization(5, validation_patches)

"""#### validation function 
- load model
- patch defectness detect(by patch_threshold)
- image defectness detect(by patch_num_threshold)
"""

"""
defect로 판단된 patch 개수가 threshold이상이면,
해당 이미지를 defect로 판단하여 True를 return한다.
"""
def image_prediction(patch_num_threshold, defectness_list):
  defect_num = sum(defectness_list)
  if (defect_num >= patch_num_threshold):
    return True # defect patch가 k개 이상이면, 해당 이미지는 defect(True)
  return False

"""
patch 한 개에 대한 loss값이 threshold이상이면,
해당 patch를 defect를 판단하여 True를 return한다.
"""
def patch_prediction(loss, patch_threshold):
  if loss >= patch_threshold :
    return True
  else: 
    return False

"""
validation의 역할
1. patch threshold, image threshold 설정
2. 모델 성능평가: 
   model4개에 대해 patch threshold 3가지, image threshold 3가지를 적용
  --> f1 score가 가장 높은 모델과 threshold 선택
"""
def validation(model_num, validation_patches, k, threshold, cm):

  TP = 0
  TN = 0
  FN = 0 
  FP = 0
  img_idx = 0
  loss_func = nn.MSELoss()
  models = [Autoencoder1().to(device), Autoencoder2().to(device), 
            Autoencoder3().to(device), Autoencoder4().to(device)]
  new_model= models[model_num-1]
  new_model.load_state_dict(torch.load("/content/drive/Shared drives/data/nocrop/model/hs/model{}/Autoencoder{}_epoch19.pth".format(model_num,model_num)))
  
  new_model.eval()
  y_true=[]
  y_pred=[]
  
  ## 한 이미지에 들어있는 patch들을 매 loop마다 불러온다. 
  ## 즉, 256개의 패치를 256, 64, 64 사이즈의 텐서로 불러온다.
  for patch in validation_patches:

    ## 원본 이미지들의 true label을 y_true에 저장
    if img_idx<28:
        y_true.append(0) #정상
    else:
        y_true.append(1)
    defectness_list = []
    
    ## 각 패치를 매 loop마다 불러온다.
    for patch_idx in range(256):
      one_patch = patch[patch_idx].view(1,1,64,64)
      one_patch = Variable(one_patch).cuda()
      pred = new_model(one_patch)
      loss = loss_func(pred, one_patch)
      # 각 patch의 결함여부가 T / F값으로 저장됨
      defectness = patch_prediction(loss, threshold ) 
      defectness_list.append(defectness)
    # 각 이미지의 결함여부가 T / F값으로 저장됨
    image_defectness = image_prediction(k, defectness_list)

    if img_idx < 28: # 실제 정상
      if image_defectness == True: #결함 판단(오류)
        FN += 1
        y_pred.append(1)
      else: # 정상 판단
        TN += 1
        y_pred.append(0)
    else: # 실제 결함
      if image_defectness == True: # 결함 판단
        TP += 1
        y_pred.append(1)
      else: # 정상 판단(오류)
        FP += 1 # want to minimize
        y_pred.append(0)
   
    img_idx += 1

  print("true:  정상  결함")
  print("pred: ", TN, " ", FP)
  print("      ", FN, " ", TP)

  f1score = f1_score(y_true, y_pred)
  accuracy = accuracy_score(y_true, y_pred)
  print("f1score=", f1score)
  print("accuracy=", accuracy)
  
  if cm == True:
    confusion_matrix2= confusion_matrix(y_true, y_pred)
    sns.heatmap(confusion_matrix2.T, annot=True,fmt='d',
                xticklabels=['nodefect','defect'], yticklabels=['nodefect','defect'], cmap="YlGnBu")
    plt.xlabel('true')
    plt.ylabel('predicted')
    plt.title('Confusion Matirx', fontsize=20)

  return f1score # 높을수록 성능 good

"""

```

'''
    REAL        정상              결함
PRED
정상      TN(정상-정상판단) FP(결함-정상판단)
결함      FN(정상-결함판단) TP(결함-결함판단)
'''
```
"""

## 모델마다 9가지의 f1score를 저장

model_f1score =  torch.zeros(4,3,3)
image_threshold = [3,5,7]
patch_threshold = [0.0028, 0.005, 0.01]
# 모델 1~4
for model_num in range(1,5):
  print()
  print()
  print("model: Autoencoder", model_num)
  ## grid search
  # image_threshold 값이 하나씩 들어간다.
  for k in range(len(image_threshold)):
    # patch_threshold 값이 하나씩 들어간다.
    for j in range(len(patch_threshold)):
      print("image_threshold: ", image_threshold[k], "patch_threshold: ", patch_threshold[j])
      model_f1score[model_num-1][k][j] = validation(model_num, validation_patches, image_threshold[k], patch_threshold[j], False)

print(model_f1score)

"""** best:model 4 **
- image_threshold:  3
- patch_threshold:  0.0028
- f1score= 0.8793
"""

# best model의 Confusion matrix 출력
validation(4, validation_patches, 3, 0.0028, True)

"""## step4: test

"""

def test_img(model_path, test_images):
  global patch
  test_patches = patch(test_images)

  loss_func = nn.MSELoss()
  new_model = Autoencoder4().to(device)
  new_model.load_state_dict(torch.load(model_path))
  new_model.eval()
  FP=0;TP=0;TN=0;FN=0;
  y_true = []
  y_pred = []
  img_idx=0
  for patch in test_patches:

    if img_idx<28:
        y_true.append(0) #정상
    else:
        y_true.append(1)

    defectness_list = []
    for patch_idx in range(256):
      one_patch = patch[patch_idx].view(1,1,64,64)
      one_patch = Variable(one_patch).cuda()
      pred = new_model(one_patch)
      loss = loss_func(pred, one_patch)
      defectness = patch_prediction(loss, 0.0028) # T / F값이 리턴됨

      defectness_list.append(defectness)
    image_defectness = image_prediction(3, defectness_list)

    if img_idx < 28:
      if image_defectness == True:
        y_pred.append(1)
      else:
        y_pred.append(0)
    else:
      if image_defectness == True:
        y_pred.append(1)
      else:
        y_pred.append(0)

    plt.imshow(np.transpose(test_images[img_idx].view(256,4096), (0, 1)), cmap="gray")
    plt.show()
    print("patch defect is {}.".format(sum(defectness_list)))
    if image_defectness == True:
      print("fabric #",img_idx," is DEFECT.")
    else:
      print("fabric #",img_idx," is nodefect.")
    print()
    print()
    img_idx +=1
  
  print("f1score = ",f1_score(y_true, y_pred))
  
  confusion_matrix2= confusion_matrix(y_true, y_pred)
  sns.heatmap(confusion_matrix2.T, annot=True,fmt='d',
              xticklabels=['nodefect','defect'], yticklabels=['nodefect','defect'],cmap="YlGnBu")
  plt.xlabel('true')
  plt.ylabel('predicted')
  plt.title('Confusion Matirx', fontsize=20)

model_path = "/content/drive/Shared drives/data/nocrop/model/hs/Autoencoder4.pth" # 성능평가에서 제일 좋았던 걸로 선택
image_path =  "/content/drive/Shared drives/data/nocrop/test/*.png"
test_images = [cv2.imread(file, cv2.IMREAD_GRAYSCALE) for file in sorted(glob.glob(image_path))]

def patch(images):
  patch_size = 64
  global patch
  global patches
  for i in range(len(images)):
    images[i] = transforms.ToTensor()((images[i]))
    # unfold로 shape조절 --> view --> [patch개수, patch_size, patch_size]
    patches = images[i].data.unfold(1, patch_size, patch_size).unfold(2, patch_size, patch_size) 
    patches = patches.contiguous().view(-1, patch_size, patch_size) 

    if i == 0:
      patch = patches
    if i > 0:
      patches = torch.cat((patch, patches))
      patch = patches

  patches = patches.view(len(images), -1, patch_size, patch_size) 
  return patches

test_img(model_path, test_images) # 3 0.0028