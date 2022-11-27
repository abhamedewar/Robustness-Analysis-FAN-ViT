import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm  # Displays a progress bar
import os
import torch
from torch import nn
from torch import optim
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import Subset, DataLoader
import matplotlib.pyplot as plt
from FAN.models import fan
from timm.models import create_model
import json
import random
import foolbox as fb
from foolbox import PyTorchModel
from foolbox.attacks import EADAttack
from attacks.FGSM import testFGSM
from attacks.PGD import testPGD
from attacks.BIM import testBIM
from attacks.Mim import testMiM
from attacks.CW import testCW
import time
import timm

with open("labels.txt") as f:
    data = f.read()
# reconstructing the data as a dictionary
ground_labels = json.loads(data)

epsilon = 25/255
device = "cuda" if torch.cuda.is_available() else "cpu"

model_path = "./pretrained_models/fan_vit_tiny.pth.tar"
print("Loading datasets...")
imagenet_path = r"./val"
normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
transform = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ]
)
imagenet_data = datasets.ImageFolder(imagenet_path, transform=transform)
val_data_loader = DataLoader(imagenet_data, batch_size=1, shuffle=True, num_workers=0)

# load model
model = create_model("fan_tiny_12_p16_224", img_size=224).to(device)
model.load_state_dict(torch.load(model_path, map_location="cpu"))
model.eval()

# get validation accuracy without attack
accuracy = 0
for val_batch, val_label in tqdm(val_data_loader):
    val_batch = val_batch.to(device)
    val_label = val_label.to(device)
    pred = model(val_batch)
    prediction = torch.argmax(pred[0].cpu()).numpy()
    label = val_label.cpu().numpy()[0]
    if prediction == label:
        accuracy += 1
    break

print(f"Model accuracy = {(accuracy/50000)*100}")

acc_FGSM, ex_FGSM = testFGSM(model, device, val_data_loader, epsilon)

for steps in [1, 2, 5, 10]:
    acc_PGD, ex_PGD = testPGD(model, device, val_data_loader, epsilon, steps)

for steps in [1, 2, 5, 10]:
    acc_BIM, ex_BIM = testBIM(model, device, val_data_loader, epsilon, steps)

acc_CW, ex_CW = testCW(model, device, val_data_loader, epsilon, 50)

acc_Mim, ex_Mim = testMiM(model, device, val_data_loader, epsilon, 10)

def show_adversarial_images(examples, labels, initial_name):
    for j in range(len(examples)):
        plt.xticks([], [])
        plt.yticks([], [])
        orig, adv, ex = examples[j]
        plt.title("{} -> {}".format(labels[str(orig)], labels[str(adv)]))
        plt.imshow(ex[0].T)
        name = initial_name + time.strftime("%Y%m%d-%H%M%S") + ".png"
        plt.savefig("./" + name)
        plt.show()

show_adversarial_images(ex_FGSM, ground_labels, "fsgm_")
# show_adversarial_images(ex_PGD,ground_labels, 'pgd_')
# show_adversarial_images(ex_BIM,ground_labels,'bim_')

#baseline ViT(DeiT-S)
def baselineViT(device, val_data_loader):
	print('Using Imagenet DeiT-S...')
    #get the model from torch hub
	model = torch.hub.load('facebookresearch/deit:main', 'deit_base_patch16_224', pretrained=True).to(device)
	model.eval()
	accuracy = 0
	for val_batch, val_label in tqdm(val_data_loader):
		val_batch = val_batch.to(device)
		val_label = val_label.to(device)
		pred = model(val_batch)
		prediction = torch.argmax(pred[0].cpu()).numpy()
		label = val_label.cpu().numpy()[0]
		if prediction == label :
			accuracy += 1
	print(f"Model accuracy = {(accuracy/50000)*100}")

baselineViT(device, val_data_loader)
