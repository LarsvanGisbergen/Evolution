# src/nn.py
import torch
import torch.nn as nn
import numpy as np


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}") # This will print 'cuda' or 'cpu' to your console

# Use Tanh activation function, same as before
activation_func = nn.Tanh()

class NeuralNetwork(nn.Module):
    def __init__(self, layer_sizes):
        """
        Initializes the neural network using PyTorch.
        layer_sizes: A list of integers for input, hidden, and output layers.
        """
        super().__init__()
        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes) - 1):
            self.layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))

    def forward(self, x):
        """
        Performs a forward pass. The input x must be a PyTorch tensor.
        """
        for i, layer in enumerate(self.layers):
            x = layer(x)
            # Apply activation function to all but the final output layer
            if i < len(self.layers) - 1:
                x = activation_func(x)
        return x

    def get_genome(self):
        """Extracts all weights and biases and flattens them into a 1D NumPy array."""
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
            # Calculate the number of elements in the current parameter tensor
            num_elements = param.numel()
            # Slice the genome to get the values for this parameter
            chunk = genome[pointer : pointer + num_elements]
            # Reshape the chunk to match the parameter's shape and load it
            param.data = torch.from_numpy(chunk).reshape(param.shape).float()
            # Move the pointer
            pointer += num_elements
    
    def calculate_genome_length(self):
        """Calculates the total number of weights and biases."""
        return sum(p.numel() for p in self.parameters())