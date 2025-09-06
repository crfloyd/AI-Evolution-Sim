import numpy as np

class NeuralNetwork:
    def __init__(self, input_size, hidden_size=14, output_size=2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        # Xavier init
        self.w1 = np.random.randn(hidden_size, input_size) * np.sqrt(1 / input_size)
        self.b1 = np.zeros((hidden_size, 1))
        self.w2 = np.random.randn(output_size, hidden_size) * np.sqrt(1 / hidden_size)
        # self.b2 = np.zeros((output_size, 1))
        self.b2 = np.random.randn(output_size, 1) * 0.01
        

    def activate(self, x):
        return np.tanh(x)
    

    def forward(self, input_array):
        x = np.array(input_array).reshape(-1, 1)
        assert x.shape[0] == self.input_size, f"Expected {self.input_size} inputs, got {x.shape[0]}"
        h = self.activate(self.w1 @ x + self.b1)
        o = self.activate(self.w2 @ h + self.b2)
        return o.flatten()
    
    
    def copy_with_mutation(self, mutation_rate=0.05, num_rays=None):
        new_input_size = num_rays if num_rays is not None else self.input_size
        clone = NeuralNetwork(new_input_size, self.hidden_size, self.output_size)

        min_inputs = min(self.input_size, new_input_size)
        
        # Copy and mutate w1 (input to hidden layer)
        clone.w1[:, :min_inputs] = self.w1[:, :min_inputs]
        if new_input_size > self.input_size:
            # Initialize new input weights randomly for expanded inputs
            clone.w1[:, min_inputs:] = np.random.randn(self.hidden_size, new_input_size - min_inputs) * np.sqrt(1 / new_input_size)
        
        # Apply mutations to all layers
        w1_mutations = np.random.randn(*clone.w1.shape) * mutation_rate
        b1_mutations = np.random.randn(*self.b1.shape) * mutation_rate
        w2_mutations = np.random.randn(*self.w2.shape) * mutation_rate
        b2_mutations = np.random.randn(*self.b2.shape) * mutation_rate
        
        clone.w1 = clone.w1 + w1_mutations
        clone.b1 = self.b1 + b1_mutations
        clone.w2 = self.w2 + w2_mutations
        clone.b2 = self.b2 + b2_mutations
        
        # Calculate mutation strength (average absolute change across all layers)
        mutation_strength = (np.mean(np.abs(w1_mutations)) + np.mean(np.abs(b1_mutations)) + 
                           np.mean(np.abs(w2_mutations)) + np.mean(np.abs(b2_mutations))) / 4
        
        clone.input_size = new_input_size  # ✅ Fix
        clone._mutation_strength = mutation_strength
        return clone


    def resize_input(self, new_num_inputs):
        clone = NeuralNetwork(new_num_inputs, self.hidden_size, self.output_size)
        min_inputs = min(self.input_size, new_num_inputs)
        clone.w1[:, :min_inputs] = self.w1[:, :min_inputs]
        clone.b1 = self.b1.copy()
        clone.w2 = self.w2.copy()
        clone.b2 = self.b2.copy()
        clone.input_size = new_num_inputs  # ✅ Fix
        return clone





