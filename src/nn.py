# src/nn.py
import torch
import torch.nn as nn
import numpy as np

# This part is correct and stays the same
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

activation_func = nn.Tanh()

class NeuralNetwork(nn.Module):
    def __init__(self, layer_sizes):
        super().__init__()
        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes) - 1):
            self.layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))

    def forward(self, x):
        for i, layer in enumerate(self.layers):
            x = layer(x)
            if i < len(self.layers) - 1:
                x = activation_func(x)
        return x

    def get_genome(self):
        genome = []
        for param in self.parameters():
            genome.append(param.data.detach().cpu().numpy().flatten())
        return np.concatenate(genome)

    def set_genome(self, genome):
        """
        Sets the network's weights and biases from a 1D NumPy array genome.
        """
        if not isinstance(genome, np.ndarray):
            genome = np.array(genome)
            
        pointer = 0
        for param in self.parameters():
            num_elements = param.numel()
            chunk = genome[pointer : pointer + num_elements]
            
            # --- THIS IS THE FIX ---
            # Create the tensor from numpy, reshape it, and THEN send it to the correct device
            # before assigning it to the parameter.
            param.data = torch.from_numpy(chunk).reshape(param.shape).float().to(DEVICE)
            
            pointer += num_elements
    
    def calculate_genome_length(self):
        return sum(p.numel() for p in self.parameters())