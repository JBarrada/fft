#defineSWAP(a,b)tempr=(a);(a)=(b);(b)=tempr
//tempr is a variable from our FFT function


//data -> float array that represent the array of complex samples
//number_of_complex_samples -> number of samples (N^2 order number) 
//isign -> 1 to calculate FFT and -1 to calculate Reverse FFT
float FFT (float data[], unsigned long number_of_complex_samples, int isign)
{
    //variables for trigonometric recurrences
    unsigned long n,mmax,m,j,istep,i;
    double wtemp,wr,wpr,wpi,wi,theta,tempr,tempi;
	
	//the complex array is real+complex so the array 
	//as a size n = 2* number of complex samples
	// real part is the data[index] and the complex part is the data[index+1]
	n=number_of_complex_samples * 2;

	//binary inversion (note that 
	//the indexes start from 1 witch means that the
	//real part of the complex is on the odd-indexes
	//and the complex part is on the even-indexes
	j=1;
	for (i=1;i<n;i+=2) {
		if (j > i) {
			//swap the real part
			SWAP(data[j],data[i]);
			//swap the complex part
			SWAP(data[j+1],data[i+1]);
		}
		m=n/2;
		while (m >= 2 && j > m) {
			j -= m;
			m = m/2;
		}
		j += m;
	}
	
	//Danielson-Lanzcos routine 
	mmax=2;
	//external loop
	while (n > mmax)
	{
		istep = mmax<<  1;
		theta=sinal*(2*pi/mmax);
		wtemp=sin(0.5*theta);
		wpr = -2.0*wtemp*wtemp;
		wpi=sin(theta);
		wr=1.0;
		wi=0.0;
		//internal loops
		for (m=1;m<mmax;m+=2) {
			for (i= m;i<=n;i+=istep) {
				j=i+mmax;
				tempr=wr*data[j-1]-wi*data[j];
				tempi=wr*data[j]+wi*data[j-1];
				data[j-1]=data[i-1]-tempr;
				data[j]=data[i]-tempi;
				data[i-1] += tempr;
				data[i] += tempi;
			}
			wr=(wtemp=wr)*wpr-wi*wpi+wr;
			wi=wi*wpr+wtemp*wpi+wi;
		}
		mmax=istep;
	}
}