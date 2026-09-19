using System.ServiceModel;
using System.Threading.Tasks;

namespace GCUService.WCFService;

[ServiceContract]
public interface IDataCallback
{
	[OperationContract(IsOneWay = true)]
	Task ReceiveData(string code, string value);
}
