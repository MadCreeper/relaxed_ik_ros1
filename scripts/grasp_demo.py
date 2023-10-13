import ctypes
import numpy as np
import os, time, sys
import sys
import transformations as T
import yaml

from urdf_parser_py.urdf import URDF
from kdl_parser import kdl_tree_from_urdf_model
import PyKDL as kdl
from robot import Robot


# make python find the package
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)) + '/../')
from relaxed_ik_core.wrappers.python_wrapper import RelaxedIKRust, lib




class RelaxedIKDemo:
    def __init__(self, path_to_src):


        setting_file_path = path_to_src + '/configs/settings.yaml'

        # os.chdir(path_to_src)

        # Load the infomation
        
        print("setting_file_path: ", setting_file_path)
        setting_file = open(setting_file_path, 'r')
        settings = yaml.load(setting_file, Loader=yaml.FullLoader)
       
      
        self.robot = Robot(setting_file_path, path_to_src, use_ros=False)
        print(f"Robot Articulated Joint names: {self.robot.articulated_joint_names}")
        
        print('\nInitialize Solver...\n')
        self.relaxed_ik = RelaxedIKRust(setting_file_path)
        
        ##DEBUG
        self.setting_file_path = setting_file_path

        if 'starting_config' not in settings:
            settings['starting_config'] = [0.0] * len(self.robot.articulated_joint_names)
        else:
            assert len(settings['starting_config']) == len(self.robot.articulated_joint_names), \
                    "Starting config length does not match the number of joints"
           
        
        self.weight_names  = self.relaxed_ik.get_objective_weight_names()
        self.weight_priors = self.relaxed_ik.get_objective_weight_priors()
        print(self.weight_names)
        print(self.weight_priors)
        
        print(len([1 for x in self.weight_names if 'selfcollision' in x]), 'self collision pairs')
        print("\nSolver RelaxedIK initialized!\n")

    def reload_ik_rust(self):
        self.relaxed_ik.__exit__(None, None, None)
        del self.relaxed_ik
        self.relaxed_ik = RelaxedIKRust(self.setting_file_path)
        
    def get_ee_pose(self):
        ee_poses = self.relaxed_ik.get_ee_positions()
        ee_poses = np.array(ee_poses)
        ee_poses = ee_poses.reshape((len(ee_poses)//6, 6))
        ee_poses = ee_poses.tolist()
        return ee_poses

    def reset_cb(self, msg):
        n = len(msg.position)
        x = (ctypes.c_double * n)()
        for i in range(n):
            x[i] = msg.position[i]
        self.relaxed_ik.reset(x)
    
    def reset(self, joint_angles):
        n = len(joint_angles)
        x = (ctypes.c_double * n)()
        for i in range(n):
            x[i] = joint_angles[i]
        return self.relaxed_ik.reset(x)
    
    def query_loss(self, joint_angles):
        n = len(joint_angles)
        x = (ctypes.c_double * n)()
        for i in range(n):
            x[i] = joint_angles[i]
        return self.relaxed_ik.get_jointstate_loss(x)

    def solve_pose_goals(self, positions, orientations, tolerances):
        # t0 = time.time()
        ik_solution = self.relaxed_ik.solve_position(positions, orientations, tolerances)
        # print(self.robot.articulated_joint_names)
        # print(ik_solution)
        # print(f"{(time.time() - t0)*1000:.2f}ms")
        return ik_solution
    
    
    def ik_update_weight_cb(self, msg):
        self.update_objective_weights({
            msg.weight_name : msg.value
        })
    
    def update_objective_weights(self, weights_dict: dict):
        if not weights_dict:
            return 
        print(weights_dict)
        
        for k in weights_dict:
            if k not in self.weight_names:
                raise KeyError(k)
        for i in range(len(self.weight_names)):
            weight_name = self.weight_names[i]
            if weight_name in weights_dict:
                self.weight_priors[i] = weights_dict[weight_name]
        self.relaxed_ik.set_objective_weight_priors(self.weight_priors)
            
    
    
if __name__ == '__main__':
    path_to_src = os.path.dirname(os.path.abspath(__file__)) + '/../relaxed_ik_core'
    print(path_to_src)
    relaxed_ik = RelaxedIKDemo(path_to_src)
    # N = number of end effectors. N = 2 in this example
    # positions: 3*N 
    # orientations: 4*N (quaternions)
    # tolerances: 6*N
    
    positions = [0.039331, 0.091392, -0.057363, 0.063934, 0.091392, 0.027384]               # x0 y0 z0 x1 y1 z1
    orientations = [0.0, 0.0 ,0.0, 1.0, 0.0, 0.0 ,0.0, 1.0]   # x0 y0 z0 w0 x1 y1 z1 w1
    tolerances = [0,0,0,0,0,0,0,0,0,0,0,0]                    
    
    # relaxed_ik.update_objective_weights({
        
    # })
    
    # allegro hand
    # positions = list(np.array([0.18671839, 0.29608066, 0.17582884]) - np.array([0.15, 0.15, 0.15])) + list(np.array([0.27055018, 0.24076818, 0.1409142]) -np.array([0.15, 0.15, 0.15]))
    # ## set ik solver 
    # weights = relaxed_ik.weight_priors[:]
    # for i in range(0, 3):
    #     weights[i] = 50
    # for i in range(3, 6):
    #     weights[i] = 0
    # weights[6] = 50
    # for i in range(7, 10):
    #     weights[i] = 50
    # for i in range(10, 13):
    #     weights[i] = 0
    # weights[13] = 50
    # for i in range(32, len(weights)):
    #     weights[i] = 0

    # relaxed_ik.relaxed_ik.set_objective_weight_priors(weights)
    
    ###################
    N = 5
    run_times = []
    
    
    # pcd_w = [10.0, 5.0, 1.0, 0.1, 0.01]
    pcd_w = [50.0, 50.0, 10.0, 10.0, 5.0, 1.0, 0.1, 0.01, 0.01, 0.01]
    # pcd_w = [50.0, 50.0]
    ee_w  = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    # pcd_w = [0.0, 0.0, 0.0, 0.0,0.0, 0.0, 0.0, 0.0,]
    N = len(pcd_w)
    relaxed_ik.update_objective_weights({
        "eepos_0": 100.0,
        "eepos_1": 100.0
    })
    joint_angle_list = []
    
    for i in range(N):
        print("-"*50)
        t0 = time.time()
        ja = relaxed_ik.solve_pose_goals(positions, orientations, tolerances)
        joint_angle_list.append(ja)
        print("Joint Angles:", ja)
        t1 = time.time()
        # positions[1] += 0.001
        run_times.append(t1 - t0)
        print('loss:', relaxed_ik.query_loss(ja))  
        print(f"time: {(t1 - t0)*1000}ms")
        
        
        relaxed_ik.update_objective_weights({
            "envcollision_pcd_0" : pcd_w[i],
            "envcollision_pcd_1" : pcd_w[i],
            "eepos_0": ee_w[i],
            "eepos_0": ee_w[i],
        })

        print("-"*50)
    
    print(f"Average time: {sum(run_times) / len(run_times) * 1000: .3f} ms.")
    np.save('/home/madcreeper/ik_recover/grasp_traj.npy', np.array(joint_angle_list))
    
    
    
    