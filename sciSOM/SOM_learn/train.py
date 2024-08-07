import numpy as np
from scipy.spatial.distance import cdist
import math
import random # Might want to take a closer look at radom number generators in the futuer

class SOM:
    __doc__ = """
    SOM class:
    SOM object that can be trained and used to classify data.
    One of the goals of this object will be to switch between different
    SOM implementations. For now, it will be a simple implementation and the 
    cSOM implementation.
    """

    def __init__(self, 
                 x_dim: int, 
                 y_dim: int, 
                 input_dim: int, 
                 n_iter: int, 
                 learning_parameters: np.ndarray, 
                 decay_type: str = "exponential", 
                 neighborhood_decay: str = "geometric_series",
                 som_type: str="Kohonen", 
                 mode: str="batch"):
        """
        Initialize the SOM object.

        Parameters:
        x_dim (int): The x dimension of the SOM.
        y_dim (int): The y dimension of the SOM.
        input_dim (int): The dimension of the input data.
        n_iter (int): The number of iterations to train the SOM.

        learning_parameters (structured array): 
        for Khononen SOM -> The learning rate and sigma for the SOM.
        for a cSOM -> The learning rate, beta, and gamma of the SOM.
        (The main difference between this paper and our implementation
        is that we also update the immidiate neighbors of the BMU)
        https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=23839
        ** Could maybe make it more general in the future so it can accept tables**

        decay_type (str): The type of decay the SOM should follow.
        som_type (str): The type of SOM to use. Current options are Kohonen or cSOM, 
                        this can be expanded.
        mode (str): The mode of the SOM. Either batch or online.

        learning_parameters['alpha'] (float): The learning rate of the SOM.
        learning_parameters['sigma'] (float): The initial neighborhood radius of the SOM.
        """
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.input_dim = input_dim
        self.n_iter = n_iter
        self.learning_parameters = learning_parameters
        self.decay_type = decay_type
        self.som_type = som_type
        self.mode = mode
        self.neighborhood_decay = neighborhood_decay
        self.weight_cube = np.random.rand(x_dim, y_dim, input_dim)
        self.is_trained = False

        self.mode_methods = {
            'batch': self._train_batch,
            'online': self._train_online
        }
        
        if mode not in self.mode_methods:
            raise ValueError(f"Mode {mode} is not supported. Choose from {list(self.mode_methods.keys())}")
        
        # Check if the learning parameters are correct
        self.learning_rate_history = np.zeros(n_iter)
        self.learning_radius_history = np.zeros(n_iter)


    def train(self, data):
        """
        Train the SOM object.

        Parameters:
        data (np.array): The data to train the SOM on.
        """
        # Check if the learning parameters are correct
        check_field_exists(self.learning_parameters, "alpha")

        # Decide the order of the input for traiing:
        train_method = self.mode_methods.get(self.mode)
       
        # Maybe output an array with random indexes to train the SOM?
        data_shuffled_index = train_method(data)

        # Train the SOM
        if self.som_type == "Kohonen":
            self.Kohonen_SOM(data, data_shuffled_index)

        elif self.som_type == "cSOM":
            self.cSOM(data, data_shuffled_index)   

        else:
            raise ValueError(f"SOM type {self.som_type} is not supported. Choose from Kohonen or cSOM")

        self.is_trained = True

    def Kohonen_SOM(self, data, indecies):
        """
        Train the SOM using the Kohonen algorithm.
        """

        # This might be a bit unnecessary but I will keep it for now.
        [som_x, som_y, _] = self.weight_cube.shape

        # Records parameters to confirm SOM is training correctly
        alpha_rec = np.zeros(self.n_iter)
        sigma_rec = np.zeros(self.n_iter)
        radius_rec = np.zeros(self.n_iter)

        # Might want to pick a mode outside the loop to save time.

        for i in range(self.n_iter):
            distances = cdist(self.weight_cube.reshape(-1, 
                                                       self.weight_cube.shape[-1]), 
                                                       data[int(indecies[i])].reshape(1,self.input_dim), 
                                                       metric='euclidean')

            w_neuron = np.argmin(distances, axis=0)
            x_idx, y_idx = np.unravel_index(w_neuron, (self.x_dim, self.y_dim))

            # Need to calculate the sigma radius.
            # Might want to write this in a more modular way.
            if self.decay_type == "exponential":
                tao = self.n_iter / self.learning_parameters["max_radius"]
                sigma = int(self.learning_parameters["sigma"] * np.exp(-i / tao))
                alpha = self.learning_parameters["alpha"] * np.exp(-i / tao)
                radius = math.ceil(self.learning_parameters["max_radius"] * np.exp(-i / tao))
            
            elif self.decay_type == "linear":
                #tao = self.n_iter / self.learning_parameters["max_radius"]
                sigma = int(self.learning_parameters["sigma"] - self.learning_parameters["sigma"] / self.n_iter * i)
                alpha = self.learning_parameters["alpha"] - self.learning_parameters["alpha"] / self.n_iter * i
                radius = math.ceil(self.learning_parameters["max_radius"] - self.learning_parameters["max_radius"] / self.n_iter * i)
           
            elif self.decay_type == "schedule":
                # Need to check if the current time step is and pic the sigma from the schedule.
                current_schedule = np.sum(self.learning_parameters["time"] <= i)
                sigma = self.learning_parameters["sigma"][current_schedule]
                alpha = self.learning_parameters["alpha"][current_schedule] 
                radius = self.learning_parameters["max_radius"][current_schedule]  

            else:
                raise ValueError(f"Decay type {self.decay_type} is not supported. Choose from exponential, linear or schedule")

            # Now compute the neighbors to update
            x_min, x_max, y_min, y_max = self.compute_neighborhood(x_idx, 
                                                                   y_idx, 
                                                                   sigma, 
                                                                   radius)

            neighborhood_radius = self.neighborhood_function(int(x_idx), 
                                                             int(y_idx), 
                                                             sigma, 
                                                             radius)
            
            self.learning_rate_history[i] = alpha
            self.learning_radius_history[i] = radius

            # This is currently updating the BMU, but we need to update the BMU and its neighbors.
            # Missing the radius decay. (further away points should be updated less)
            self.weight_cube[x_min:x_max, y_min:y_max] += (
                alpha 
                * neighborhood_radius[x_min:x_max, y_min:y_max, np.newaxis] 
                * (data[int(indecies[i])] - self.weight_cube[x_min:x_max, y_min:y_max]))
            
    
    def cSOM(self, index):
        """
        Train the SOM using the concious SOM algorithm.
        """
        raise NotImplementedError
    
    def neighborhood_function(self, x_bmu, y_bmu, sigma, radius):
        """
        Calculate the neighborhood function for the SOM. This function should
        decay with the distance from the BMU.
        """
        x_min, x_max, y_min, y_max = self.compute_neighborhood(x_bmu, y_bmu, sigma, radius)
        update_neighborhood = np.zeros((self.x_dim, self.y_dim))

        # Simple neighborhood function
        #-=]\update_neighborhood[x_min:x_max, y_min:y_max] = 1 

        # Could maybe speed up with numba
        # Make tests to ensure BMU is ser to 1 and decays with distance
        if self.neighborhood_decay == "geometric_series":
            for i in range(x_min, x_max):
                for j in range(y_min, y_max):

                    update_neighborhood[i, j] = 1 / 2 ** (max((np.abs(x_bmu - i)), np.abs(y_bmu - j) )) #np.exp(-np.linalg.norm([i-x_bmu, j-y_bmu]) / sigma)

        elif self.neighborhood_decay == "exponential":
            for i in range(x_min, x_max):
                for j in range(y_min, y_max):
                    update_neighborhood[i, j] = np.exp(-np.linalg.norm([i-x_bmu, j-y_bmu]) ** 2 / (2 * radius ** 2))

        elif self.neighborhood_decay == "none":
            update_neighborhood[x_min:x_max:, y_min: y_max] = 1

        return update_neighborhood
        # Want to make it so the value is 1 at the BMU and decays with distance.

    
    def compute_neighborhood(self, x_bmu, y_bmu, sigma, radius):
        """
        Compute the neighborhood of the BMU.
        """
        x_min = max(0, x_bmu - radius)  
        x_max = min(self.x_dim -1, x_bmu + radius)  
        y_min = max(0, y_bmu - radius)  
        y_max = min(self.y_dim -1, y_bmu + radius)

        return int(x_min), int(x_max), int(y_min), int(y_max)

    def decay(self):
        """
        Decides how the learning rate and other parameters will decrease over time
        ** Not in use yet **
        """
        if self.decay_type == "exponential":
            self.learning_rate = self.learning_rate * np.exp(-i / self.n_iter)
            self.sigma = self.sigma * np.exp(-i / self.n_iter)

        elif self.decay_type == "linear":
            self.learning_rate = self.learning_rate - self.learning_rate / self.n_iter * i
            self.sigma = self.sigma - self.sigma / self.n_iter * i

        elif self.decay_type == "schedule":
            self

        raise NotImplementedError

    def _train_batch(self, data):
        """
        Train the SOM in batch mode.
        This is making an assumption that the data is bigger than the itteration,
        this is not always true
        """
        batches = math.ceil(self.n_iter/ len(data))
        reminder = self.n_iter % len(data) 
        indecies = np.zeros(self.n_iter)

        for batch in range(batches):
            if batch != batches - 1:
                indecies[batch*len(data): (1 + batch)*len(data)] = random.sample(list(np.arange(len(data))), len(data))
            elif reminder != 0:
                indecies[(batch)*len(data):] = random.sample(list(np.arange(len(data))), reminder)
                
        return indecies

    def _train_online(self, data):
        """
        Train the SOM in online mode.
        """
        return random.choices(np.arange(len(data)), k=self.n_iter) 
    
    def weight_cube(self):
        """
        Return the weight cube of the SOM.
        """
        return self.weight_cube



def check_field_exists(structured_array: np.ndarray, field_name: str) -> bool:
    """
    Check if a field exists in a structured array.
    """
    return field_name in structured_array.dtype.names

def log_parameters(parameters: dict):
    """
    Make a log of the parameters used to train the SOM and save this onto a file.
    """
    raise NotImplementedError