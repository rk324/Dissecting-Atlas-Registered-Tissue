import torch
import STalign
import numpy as np
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)
import tkinter as tk
from tkinter import ttk

# Modified version of STalign.LDDMM_3D_to_slice
def LDDMM_3D_LBGFS(xI,I,xJ,J,pointsI=None,pointsJ=None,
                   L=None,T=None,A=None,v=None,xv=None,
                   a=500.0,p=2.0,expand=1.25,nt=3,niter=5000,
                   sigmaM=1.0,sigmaB=2.0,sigmaA=5.0,sigmaR=1e8,sigmaP=2e1,
                   device='cpu',dtype=torch.float64, progress_bar=None):

        
    # check initial inputs and convert to torch
    if A is not None:
        # if we specify an A
        if L is not None or T is not None:
            raise Exception('If specifying A, you must not specify L or T')
        L = torch.tensor(A[:3,:3],device=device,dtype=dtype,requires_grad=True)
        T = torch.tensor(A[:3,-1],device=device,dtype=dtype,requires_grad=True)   
    else:
        # if we do not specify A                
        if L is None: L = torch.eye(3,device=device,dtype=dtype,requires_grad=True)
        if T is None: T = torch.zeros(3,device=device,dtype=dtype,requires_grad=True)
    
    L = torch.tensor(L,device=device,dtype=dtype,requires_grad=True)
    T = torch.tensor(T,device=device,dtype=dtype,requires_grad=True)
    # change to torch
    I = torch.tensor(I,device=device,dtype=dtype)                         
    J = torch.tensor(J,device=device,dtype=dtype)
    if J.ndim == 3:
        J = J[:,None] # add a z slice dimension

    if v is not None and xv is not None:
        v = torch.tensor(v,device=device,dtype=dtype,requires_grad=True)
        xv = [torch.tensor(x,device=device,dtype=dtype) for x in xv]
        XV = torch.stack(torch.meshgrid(xv),-1)
        nt = v.shape[0]        
    elif v is None and xv is None:
        minv = torch.as_tensor([x[0] for x in xI],device=device,dtype=dtype)
        maxv = torch.as_tensor([x[-1] for x in xI],device=device,dtype=dtype)
        minv,maxv = (minv+maxv)*0.5 + 0.5*torch.tensor([-1.0,1.0],device=device,dtype=dtype)[...,None]*(maxv-minv)*expand
        xv = [torch.arange(m,M,a*0.5,device=device,dtype=dtype) for m,M in zip(minv,maxv)]
        XV = torch.stack(torch.meshgrid(xv),-1)
        v = torch.zeros((nt,XV.shape[0],XV.shape[1],XV.shape[2],XV.shape[3]),device=device,dtype=dtype,requires_grad=True)  
    else:
        raise Exception(f'If inputting an initial v, must input both xv and v')
    extentV = STalign.extent_from_x(xv[1:])
    dv = torch.as_tensor([x[1]-x[0] for x in xv],device=device,dtype=dtype)
    
    fv = [torch.arange(n,device=device,dtype=dtype)/n/d for n,d in zip(XV.shape,dv)]
    extentF = STalign.extent_from_x(fv[1:])
    FV = torch.stack(torch.meshgrid(fv),-1)
    LL = (1.0 + 2.0*a**2* torch.sum( (1.0 - torch.cos(2.0*np.pi*FV*dv))/dv**2 ,-1))**(p*2.0)

    K = 1.0/LL
    
    DV = torch.prod(dv)
    Ki = torch.fft.ifftn(K).real

    # initialize weights
    WM = torch.ones(J[0].shape,dtype=J.dtype,device=J.device)*0.5
    WB = torch.ones(J[0].shape,dtype=J.dtype,device=J.device)*0.4
    WA = torch.ones(J[0].shape,dtype=J.dtype,device=J.device)*0.1

    # locations of pixels
    extentI = STalign.extent_from_x(xI[1:]) 
    xI = [torch.tensor(x,device=device,dtype=dtype) for x in xI]
    if len(xJ) == 2:
        xJ = [[0.0],xJ[0],xJ[1]]    
    extentJ = STalign.extent_from_x(xJ[1:])
    xJ = [torch.tensor(x,device=device,dtype=dtype) for x in xJ]
    XI = torch.stack(torch.meshgrid(*xI,indexing='ij'),-1)
    XJ = torch.stack(torch.meshgrid(*xJ,indexing='ij'),-1)
    dJ = [x[1]-x[0] for x in xJ[1:]]

    Esave = []
    # zero gradients
    try:
        L.grad.zero_()
    except:
        pass
    try:
        T.grad.zero_()
    except:
        pass

    if pointsI is None and pointsJ is None:
        pointsI = torch.zeros((0,2),device=J.device,dtype=J.dtype)
        pointsJ = torch.zeros((0,2),device=J.device,dtype=J.dtype)
    elif (pointsI is None and pointsJ is not None) or (pointsJ is None and pointsI is not None):
        raise Exception('Must specify corresponding sets of points or none at all')
    else:
        pointsI = torch.tensor(pointsI,device=J.device,dtype=J.dtype)
        pointsJ = torch.tensor(pointsJ,device=J.device,dtype=J.dtype)

    optimizer = torch.optim.Adam([L, T,v], lr=1e-3)#, max_iter=4, line_search_fn="strong_wolfe")
    def closure():
        optimizer.zero_grad()
        
        A = STalign.to_A_3D(L,T)

        # Ai
        Ai = torch.linalg.inv(A)
        # transform sample points        
        Xs = (Ai[:-1,:-1]@XJ[...,None])[...,0] + Ai[:-1,-1]
        
        # now diffeo, not semilagrange here
        for t in range(nt-1,-1,-1):
            Xs = Xs + STalign.interp3D(xv,-v[t].permute(3,0,1,2),Xs.permute(3,0,1,2)).permute(1,2,3,0)/nt
        
        # and points
        pointsIt = torch.clone(pointsI)
        if pointsIt.shape[0] >0:
            for t in range(nt):
                pointsIt += (STalign.interp3D(xv,v[t].permute(3,0,1,2),pointsIt.T[...,None,None])[...,0,0].T/nt)
            pointsIt = (A[:-1,:-1]@pointsIt.T + A[:-1,-1][...,None]).T 
       
        # transform image
        AI = STalign.interp3D(xI,I,Xs.permute(3,0,1,2),padding_mode="border")

        fAI = AI
        # objective function
        EM = torch.sum((fAI - J)**2*WM)/2.0/sigmaM**2
        ER = torch.sum(torch.sum(torch.abs(torch.fft.fftn(v,dim=(1,2)))**2,dim=(0,-1))*LL)*DV/2.0/v.shape[1]/v.shape[2]/sigmaR**2
            
        E = EM + ER
        
        if pointsIt.shape[0]>0:
            EP = torch.sum((pointsIt - pointsJ)**2)/2.0/sigmaP**2
            E += EP

        E.backward(retain_graph=True)
        return E
    
    for it in range(niter):
        print(f'Iteration #{it+1}:')

        torch.autograd.set_detect_anomaly(True)
        optimizer.zero_grad()        
        # make A
        A = STalign.to_A_3D(L,T)

        # Ai
        Ai = torch.linalg.inv(A)
        # transform sample points        
        Xs = (Ai[:-1,:-1]@XJ[...,None])[...,0] + Ai[:-1,-1]
        # now diffeo, not semilagrange here
        for t in range(nt-1,-1,-1):
            Xs = Xs + STalign.interp3D(xv,-v[t].permute(3,0,1,2),Xs.permute(3,0,1,2)).permute(1,2,3,0)/nt
        # # and points (not in 3D)
        
        pointsIt = torch.clone(pointsI)
        if pointsIt.shape[0] >0:
            for t in range(nt):
                pointsIt += (STalign.interp3D(xv,v[t].permute(3,0,1,2),pointsIt.T[...,None,None])[...,0,0].T/nt)
            pointsIt = (A[:-1,:-1]@pointsIt.T + A[:-1,-1][...,None]).T
        
        # transform image
        AI = STalign.interp3D(xI,I,Xs.permute(3,0,1,2),padding_mode="border")

        fAI = AI
        # objective function
        EM = torch.sum((fAI - J)**2*WM)/2.0/sigmaM**2
        ER = torch.sum(torch.sum(torch.abs(torch.fft.fftn(v,dim=(1,2)))**2,dim=(0,-1))*LL)*DV/2.0/v.shape[1]/v.shape[2]/sigmaR**2
            
        E = EM + ER
        tosave = [E.item(), EM.item(), ER.item()]
        
        if pointsIt.shape[0]>0:
            EP = torch.sum((pointsIt - pointsJ)**2)/2.0/sigmaP**2
            E += EP
            tosave.append(EP.item())
    
        E.backward()
        optimizer.step()
        Esave.append( tosave )

        if progress_bar is not None:
            progress_bar.step(1)
            progress_bar.update()

    return {
        'A': A.clone().detach(), 
        'v': v.clone().detach(), 
        'xv': xv, 
        'WM': WM.clone().detach(),
        'WB': WB.clone().detach(),
        'WA': WA.clone().detach(),
        'Xs': Xs.clone().detach()
    }

class TkFigure(Figure):

    def __init__(self, master, num_rows=1, num_cols=1, toolbar=False):
        super().__init__()
        self.canvas = FigureCanvasTkAgg(self, master)
        self.subplots(num_rows, num_cols)
    
        if toolbar:
            self.toolbar = NavigationToolbar2Tk(self.canvas, master)
            self.toolbar.update_idletasks()
        
    def get_widget(self):
        return self.canvas.get_tk_widget()

    def update(self):
        self.canvas.draw_idle()
        self.canvas.flush_events()