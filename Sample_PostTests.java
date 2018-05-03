package DevApi.sandBox;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.net.URISyntaxException;
import java.security.GeneralSecurityException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

import org.apache.http.client.ClientProtocolException;
import org.apache.log4j.Logger;
import org.json.JSONException;
import org.testng.annotations.Test;

import com.automation.framework.selenium.BaseTestHelper;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import DevApi.enums.devApi_GetEnum;
import DevApi.enums.devApi_PostEnum;
import DevApi.helpers.PostCommonHelper;
import DevApi.helpers.getCommonHelper;
import DevApi.postRequestModels.Customer.AgentLogin;
import DevApi.postRequestModels.ProductSearch.MerchantProdSearch;
import DevApi.utils.apiHelper;
import DevApi.utils.getConstants;
import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;

public class Sample_PostTests extends BaseTestHelper {

	static Logger log = Logger.getLogger(Sample_PostTests.class.getName());

	@Test
	public void createVoucher() throws ClientProtocolException, IOException, URISyntaxException, InvalidKeyException,
			NoSuchAlgorithmException, JSONException {

		Response response = DevApi.helpers.PostCommonHelper.genCreateVocherAndGetVoucherCode(getConstants.CampaignId,
				getConstants.UserType, getConstants.MerchantId);

		String message = response.jsonPath().getString("Message");
		log.info("Message : " + message);
		String[] vocher = message.split(" ");
		String part2 = vocher[3];
		log.info("vocher : " + part2);
	}

	@Test
	public void ProductSearch_RestAsrd()
			throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		String url1 = apiHelper.constructUrl(devApi_PostEnum.PostProductSearch);
		String rqst = apiHelper.createFinalPostUrl(url1);

		// Initializing payload or API body
		String payload = "InputData={\"Search\":{\"Category\":\"\",\"sku\":\"\",\"PageSize\":\"10\",\"Keyword\":\"\",\"Brand\":\"\",\"AttributeName\":{\"AttributeValueName\":\"\"},\"merchantId\":\"bd5c1517-8d80-48d7-8e8e-365433ad124f\",\"Catalogcode\":\"CU00306960\",\"PageNumber\":\"1\",\"locationid\":\"14836\",\"ProductTag\":\"\"}}&InputFormat=application/json&merchantId=bd5c1517-8d80-48d7-8e8e-365433ad124f";
		// e.g.-"{\"key1\":\"value1\",\"key2\":\"value2\"}"

		Response response = RestAssured.given().accept(ContentType.JSON)
				.contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false).body(payload).when()
				.post(rqst);

		response.then().log().all();
	}

	@Test
	public void ProductExtendedSearch_RestAsrd()
			throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		String url1 = apiHelper.constructUrl(devApi_GetEnum.ExtendedSearch);
		String rqst = apiHelper.postApi(url1, apiHelper.urlAppend(devApi_GetEnum.ExtendedSearch));

		// e.g.-"{\"key1\":\"value1\",\"key2\":\"value2\"}"
		String payload = "OutPutFields=EXT&InputData={\"Search\":{\"Category\":\"CU00306960\",\"sku\":\"\",\"PageSize\":\"10\",\"Keyword\":\"\",\"Brand\":\"\",\"AttributeName\":{\"AttributeValueName\":\"\"},\"merchantId\":\"bd5c1517-8d80-48d7-8e8e-365433ad124f\",\"Catalogcode\":\"\",\"PageNumber\":\"1\",\"locationid\":\"14838\",\"ProductTag\":\"\"}}";

		Response response = RestAssured.given().accept(ContentType.JSON)
				.contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false).body(payload).when()
				.post(rqst);

		response.then().log().all();
	}

	@Test
	public void TC_AddCartItemsFromShoppingList()
			throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		Response response = PostCommonHelper.genLogin(getConstants.Username, getConstants.Password);
		String access = response.jsonPath().getString("Token.AccessToken");
		log.info("accessToken : " + access);

		PostCommonHelper.genAddItemsToCartFromShoppingList(access, getConstants.ShoppingListUserId,
				getConstants.ShoppingListName, getConstants.ShoppingListPrivacyLevel, getConstants.ShoppingListRefCode,
				getConstants.ShoppingListItemId, getConstants.Quantity, getConstants.CartShoppingListId, "",
				getConstants.MerchantId);
	}

	@Test
	public void TC_SetDeliverySlot() throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		Response response = PostCommonHelper.genLogin(getConstants.Username, getConstants.Password);
		String access = response.jsonPath().getString("Token.AccessToken");
		log.info("accessToken : " + access);

		getCommonHelper.addToCartGen(access);
		getCommonHelper.getCartGen(access);
		Response response2 = getCommonHelper.genGetDeliverySlots(access);
		List<String> getdata = new ArrayList<String>();
		getdata.add(response2.jsonPath().getString("DaySlots.Slots[0].DeliverySlotDate[0]"));
		getdata.add(response2.jsonPath().getString("DaySlots.Slots[0].DeliverySlotID[0]"));
		log.info("deliveryslot/DeliverySlotDate : " + getdata);

		String deliverySlotdate = getdata.get(0);
		String deliverySlotId = getdata.get(1);

		// PostCommonHelper.genSetDeliverySlots(access, deliverySlotdate,
		// deliverySlotId);

	}

	@Test
	public void loginObjectToJson() throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		String url1 = apiHelper.constructUrl(devApi_PostEnum.PostLoginUser);
		String rqst = apiHelper.createFinalPostUrl(url1);
		AgentLogin agentLogin = new AgentLogin();
		agentLogin.setUsername("7799165659");
		agentLogin.setPassword("123456");
		Gson gson = new Gson();
		String payload = "InputData=" + gson.toJson(agentLogin)
				+ "&InputFormat=application/json&merchantId=48fdd16-92db-4188-854d-1ecd9b62d066";

		// String payload =
		// "InputData={\"Username\":\"7799165659\",\"Password\":\"123456\"}&InputFormat=application/json&merchantId=48fdd16-92db-4188-854d-1ecd9b62d066";
		log.info("details strinng from object>>>>>>" + payload);
		Response response = RestAssured.given().accept(ContentType.JSON)
				.contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false).body(payload).when()
				.post(rqst);

		response.then().log().all();

	}

	@Test
	public void ProductSearch_RestAsrd_Test()
			throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		String url1 = apiHelper.constructUrl(devApi_PostEnum.PostProductSearch);
		String rqst = apiHelper.createFinalPostUrl(url1);
		/*
		 * // Initializing payload or API body String payload =
		 * "InputData={\"Search\":{\"Category\":\"\",\"sku\":\"\",\"PageSize\":\"10\",\"Keyword\":\"\",\"Brand\":\"\",\"AttributeName\":{\"AttributeValueName\":\"\"},\"merchantId\":\"bd5c1517-8d80-48d7-8e8e-365433ad124f\",\"Catalogcode\":\"CU00306960\",\"PageNumber\":\"1\",\"ProductTag\":\"\"}}&InputFormat=application/json&merchantId=bd5c1517-8d80-48d7-8e8e-365433ad124f";
		 * // e.g.-"{\"key1\":\"value1\",\"key2\":\"value2\"}"
		 */
		MerchantProdSearch merchatProdSearch = new MerchantProdSearch();
		merchatProdSearch.setPageSize("10");
		merchatProdSearch.setMerchantId("bd5c1517-8d80-48d7-8e8e-365433ad124f");
		merchatProdSearch.setCatalogcode("CU00306960");
		merchatProdSearch.setPageNumber("1");
		Gson gson = new Gson();
		String payload = "InputData={\"Search\":" + gson.toJson(merchatProdSearch)
				+ "}&InputFormat=application/json&merchantId=bd5c1517-8d80-48d7-8e8e-365433ad124f";

		Response response = RestAssured.given().accept(ContentType.JSON)
				.contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false).body(payload).when()
				.post(rqst);

		response.then().log().all();
	}

	@Test
	public void json_test() throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		try {

			// log.info("Reading JSON from a
			// file"+System.getProperty(("user.dir")+"/data/devApi/Example.json"));
			String url1 = apiHelper.constructUrl(devApi_PostEnum.PostProductSearch);
			String rqst = apiHelper.createFinalPostUrl(url1);

			Gson gson = new Gson();
			BufferedReader br = new BufferedReader(
					new FileReader(System.getProperty("user.dir") + "\\data\\devApi\\Example.json"));
			MerchantProdSearch merchageProdObj = gson.fromJson(br, MerchantProdSearch.class);
			// log.info(">>>>>>>>>>>>size
			// print"+merchageProdObj.getPageSize());
			merchageProdObj.setMerchantId(getConstants.MerchantId);
			String payload = "InputData={\"Search\":" + gson.toJson(merchageProdObj)
					+ "}&InputFormat=application/json&merchantId=bd5c1517-8d80-48d7-8e8e-365433ad124f";

			Response response = RestAssured.given().accept(ContentType.JSON)
					.contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false).body(payload).when()
					.post(rqst);

			response.then().log().all();

		} catch (Exception e) {
			e.printStackTrace();
		}

	}

	@Test
	public void json_test_collection() throws IOException, GeneralSecurityException, URISyntaxException, JSONException {

		try {

			Response LoginResponse = PostCommonHelper.genLogin(getConstants.Username, getConstants.Password);
			String access = LoginResponse.jsonPath().getString("Token.AccessToken");
			log.info("accessToken : " + access);
			String url1 = apiHelper.constructUrl(devApi_PostEnum.PostAddcartitems);
			String rqst = apiHelper.createFinalPostUrl(url1);

			Gson gson = new Gson();
			BufferedReader buffer = new BufferedReader(
					new FileReader(System.getProperty("user.dir") + "\\data\\devApi\\pizzahut.json"));
			// AddCartItems addCartItemObj = gson.fromJson(br,
			// AddCartItems.class);

			JsonParser parser = new JsonParser();

			Object obj = parser
					.parse(new FileReader(System.getProperty("user.dir") + "\\data\\sandBox\\pizzahut.json"));

			JsonObject jsonObject = (JsonObject) obj;

			String payload = "InputData={\"cart\":" + jsonObject.toString()
					+ "}&InputFormat=application/json&merchantId=" + getConstants.MerchantId + "";

			// String payload1 = "{\n \"DelveryMode\": \"\",\n
			// \"IsPickupStore\": \"\",\n \"CurrencyCode\": \"\",\n
			// \"BillFirstName\": \"\",\n \"ShipCity\": \"\",\n \"ShipState\":
			// \"\",\n \"ShipCountry\": \"\",\n \"PickupEmail\": \"\",\n
			// \"PickupFirstName\": \"\",\n \"PickupLastName\": \"\",\n
			// \"PickupMobile\": \"\",\n \"AlternatePickupEmail\": \"\",\n
			// \"AlternatePickupFirstName\": \"\",\n
			// \"AlternatePickupLastName\": \"\",\n \"AlternatePickupMobile\":
			// \"\",\n \"GiftMessage\": \"\",\n \"Item\": [\n {\n \"ProductID\":
			// 12471582,\n \"VariantProductID\": 9280042,\n \"Quantity\": 1,\n
			// \"LocationCode\": \"\",\n \"LocationID\": \"14836\",\n
			// \"Status\": \"A\",\n \"CartReferenceKey\":
			// \"00000000-0000-0000-0000-000000000000\",\n \"ChildItem\": [\n
			// {\n \"ProductID\": 0,\n \"VariantProductID\": 0,\n \"Quantity\":
			// 0,\n \"Portion\": \"\",\n \"GroupID\": 0,\n \"childItem\": [\n
			// {}\n ]\n }\n ]\n }\n ]\n}";

			log.info("sample>>>>>>>>>>>>" + payload);

			// Initialize
			// AddItemProductId,AddItemVarientProductId,CartReferneKey,Quantity,ProductId,VariantProductID,MerchantId
			// to merchant data file.
			/*
			 * String payload =
			 * "InputData={\"cart\":{\"Item\":[{\"Status\":\"A\",\"ProductID\":\""
			 * + addItemProductId + "\",\"VariantProductID\":\"" +
			 * addItemVarientProductId +
			 * "\",\"LocationId\":\"18284\",\"CartReferenceKey\":\"" +
			 * CartReferneKey + "\",\"Quantity\":\"" + Quantity +
			 * "\"},{\"Status\":+\"A\",\"ProductID\":\"" + ProductId +
			 * "\",\"VariantProductID\":\"" + VarientProductId +
			 * "\",\"LocationId\":\"18284\",\"CartReferenceKey\":\"" +
			 * CartReferneKey + "\",\"Quantity\":\"" + Quantity +
			 * "\"}]}}&InputFormat=application/json&merchantId=" + merchantId +
			 * "";
			 */

			Response response = RestAssured.given().header("AccessToken", access).accept(ContentType.JSON)
					.header("Version", "3").contentType("application/x-www-form-urlencoded").urlEncodingEnabled(false)
					.body(payload).when().post(rqst);

			response.then().log().all();

		} catch (Exception e) {
			e.printStackTrace();
		}

	}

}