import viff
import numpy as np

def save_khoros_raw(file_name: str, data: np.ndarray):
    """
    Saves a given data into the desired raw data file so I can use 
    it to train an SOM in NeuroScope.

    Parameters
    ----------
    
    file_name : str
        Path to where you want to save the file + file name
    data : np.ndarray
        Data for the weightcube to use in neuroscope
    """
    import viff
    
    [Length, Width, Height] = np.shape(data)
    save_khoros_raw = np.reshape(data.transpose(2,1,0), [1, Height, Length, Width])
    save_khoros_raw_c = np.ascontiguousarray(save_khoros_raw)
    assert '.raw' in file_name, "The output file must be a raw file!"
    viff.write(file_name, save_khoros_raw_c)

def import_khoros_weightcube(path_to_weights: str):
    """
    Imports a weightcube generated with the khoros system,
    reshapes it into the appropriate format and applies an
    affine transform for recalls.

    Parameters
    ----------

    path_to_weights : str
        path to where the som weight is located

    Returns
    -------
    weight_cube : np.ndarray
        The weight cube for the SOM, reshaped to be handled in python
    """
    import viff
    
    wgtcub = viff.read(path_to_weights)
    [_, zdim, xdim, ydim] = wgtcub.shape
    wgtcub_re = np.reshape(wgtcub, [zdim, xdim, ydim])
    wgtcub_tr = np.transpose(wgtcub_re, [1,2,0])
    weight_cube = affine_transform(wgtcub_tr, -1,1,0,1)
    return weight_cube

def data_to_raw_file_4_khoros(data: np.ndarray, file: str):
    """
    Make data file into an appropriate raw file for khoros format
    
    Parameters
    ----------
    
    data : np.ndarray
        3D data cube
    file : str
        path location + filename of desired output file
    """
    data_t = np.transpose(data, [2,0,1])
    np.asfortranarray(data_t.astype('float64')).tofile(file)
    print('Data has been saved')