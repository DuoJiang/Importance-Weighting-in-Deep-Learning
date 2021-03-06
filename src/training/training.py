import os
import torch
import pickle
from ..utils.utils import logging
from tqdm import tqdm
from sklearn.metrics import classification_report
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def train(model, trainloader, testloaders, criterion, optimizer, config, reloaded_fractions=[]):
    
    # Record training process
    logging(
        message="Start training the experiment: {}!".format(config.experiment_title),
        path=os.path.join(config.root, "results/logs", config.experiment_title+".txt"),
        mode="w+",
    )
    
    # Start training
    total_step = len(trainloader)
    num_epochs = config.epoch
    fractions = reloaded_fractions
    
    for epoch in range(num_epochs):
        total_loss = []
        total_batch_size = 0
        model.train()
        for i, (images, labels) in enumerate(trainloader):
            images = images.to(device)
            labels = labels.to(device)
            batch_size = images.size(0)
            
            # Forward pass
            outputs = model(images)
            loss = criterion(outputs, labels)

            # Backward and optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # accumulate loss
            total_loss.append(loss.item()*batch_size)
            total_batch_size += batch_size
            
            if (i+1) % 100 == 0:
                avg_loss = sum(total_loss)/total_batch_size
                message = "Epoch [{}/{}], Step [{}/{}], AVG Loss: {:.4f}" \
                   .format(epoch+1, num_epochs, i+1, total_step, avg_loss)
                logging(
                    message=message,
                    path=os.path.join(config.root, "results/logs", config.experiment_title+".txt"),
                    mode="a+",
                )
        
        # After each epoch, we save the model checkpoints
        checkpoints = {
            'epoch': epoch+1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'current_fraction_list': fractions,
        }
        torch.save(
            checkpoints,
            os.path.join(config.root, "results/models", config.experiment_title+".ckpt")
        )
                
        # After each epoch, we evaluate on "cat and dog test images" and "test images from the other 8 classes"
        fractions_catdog_other8 = []
        for testloader in testloaders:
            evaluation_results = evaluation(model, testloader, config)
            fractions_catdog_other8.append(evaluation_results["fraction_of_class_a"])
        fractions.append(fractions_catdog_other8)
        
        # We save fraction of dogs after each epoch in case that we will stop the training process earlier
        fractions_path=os.path.join(config.root, "results/fractions", config.experiment_title+".pkl")
        with open(fractions_path, "wb") as file:
            pickle.dump(fractions, file) 
    
    return model

def evaluation(model, testloader, config):
    model.eval()
    with torch.no_grad():
        y_trues, y_preds = [], []
        for images, labels in testloader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            y_preds += predicted.tolist()
            y_trues += labels.tolist()
        report = classification_report(y_trues, y_preds, zero_division=0)
    
    fraction_of_class_a = sum([config.class_a_index==y_pred for y_pred in y_preds])/len(y_preds)
    
    # save results
    evaluation_results = {
        "y_trues": y_trues,
        "y_preds": y_preds, 
        "report": report,
        "fraction_of_class_a": fraction_of_class_a,
    }
    return evaluation_results