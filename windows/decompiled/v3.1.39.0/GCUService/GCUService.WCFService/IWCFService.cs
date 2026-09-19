using System.ServiceModel;
using System.Threading.Tasks;

namespace GCUService.WCFService;

[ServiceContract(CallbackContract = typeof(IDataCallback))]
public interface IWCFService
{
	[OperationContract(IsOneWay = true)]
	Task StartSendingToClient(string data);

	[OperationContract]
	void SendToServer(string Topic, string Command);
}
