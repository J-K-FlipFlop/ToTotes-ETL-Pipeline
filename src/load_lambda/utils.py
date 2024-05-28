from src.load_lambda.connection import connect_to_db
from botocore.exceptions import ClientError
from pg8000.exceptions import DatabaseError
from datetime import datetime
from pprint import pprint as pp
import boto3
import logging
import pandas as pd
import re
import awswrangler as wr
from numpy import nan


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

"""Pseudocode
get data from s3 function
    all data in processed bucket in parquet format
    pass table_name.parquet as argument to get data from bucket,
    using get_object, one by one. Takes table_name, which references
    filepath of the data in the processed zone

insert data into warehouse
    want to load data one by one, so get parquet data and 
    immediately INSERT INTO warehouse, using table_name as the 
    name of the table. can INSERT directly, using read_parquet
    functionality
"""


def sql_security(table):
    conn = connect_to_db()
    table_names_unfiltered = conn.run(
        "SELECT TABLE_NAME FROM postgres.INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
    )
    regex = re.compile("(^pg_)|(^sql_)|(^_)")
    table_names_filtered = [
        item[0] for item in table_names_unfiltered if not regex.search(item[0])
    ]
    if table in table_names_filtered:
        return table
    else:
        raise DatabaseError(
            "Table not found - do not start a table name with pg_, sql_ or _"
        )


def get_latest_processed_file_list(
    client: boto3.client, timestamp_filtered: str = None
) -> dict:
    bucket = "blackwater-processed-zone"
    runtime_key = f"last_ran_at.csv"
    if not timestamp_filtered:
        get_previous_runtime = client.get_object(
            Bucket="blackwater-ingestion-zone", Key=runtime_key
        )
        timestamp = get_previous_runtime["Body"].read().decode("utf-8")
        timestamp_filtered = timestamp[12:-8]
    try:
        output = client.list_objects_v2(Bucket=bucket)
        if timestamp_filtered != "1999-12-31 23:59:59":
            file_list = [
                file["Key"]
                for file in output["Contents"]
                if timestamp_filtered in file["Key"]
            ]
        else:
            file_list = [
                file["Key"]
                for file in output["Contents"]
                if "original_data_dump" in file["Key"]
            ]
        return {
            "status": "success",
            "file_list": file_list,
        }
    except ClientError:
        return {
            "status": "failure",
            "file_list": [],
        }


def get_data_from_processed_zone(client: boto3.client, pq_key: str) -> dict:
    bucket = "blackwater-processed-zone"
    try:
        df = wr.s3.read_parquet(path=f"s3://{bucket}/{pq_key}")
        return {"status": "success", "data": df}
    except ClientError as c:
        logger.info(f"Boto3 ClientError: {str(c)}")
        return {"status": "failure", "message": c.response["Error"]["Message"]}


def get_insert_query(table_name: str, dataframe: pd.DataFrame):
    query = f"""INSERT INTO {table_name} VALUES """
    for _, row in dataframe.iterrows():
        query += f"""{tuple(row.values)}, """
    query = f"""{query[:-2]} RETURNING *;"""
    logger.info(query)
    query = query.replace("<NA>", "null")
    if table_name == 'dim_location':
        query = query.replace("le's", "les").replace('"', "'")
    logger.info(query)
    return query


def insert_data_into_data_warehouse(client: boto3.client, pq_key: str, connection):
    data = get_data_from_processed_zone(client, pq_key)
    if data["status"] == "success":
        try:
            table_name = pq_key.split("/")[-1][:-8]
            table_name = sql_security(table_name)
            query = get_insert_query(table_name=table_name, dataframe=data["data"])
            connection.run(query)
            return {
                "status": "success",
                "table_name": table_name,
                "message": "Data successfully inserted into data warehouse",
            }
        except DatabaseError as e:
            return {
                "status": "failure",
                "table_name": table_name,
                "message": "Data was not added to data warehouse",
                "Error Message": e,
            }
        # finally:
        #     connection.close()
    else:
        return data


# dim_currency_dict = [{"currency_code": 'GBP',
#                      "currency_name": 'Pound Sterling'},
#                      {"currency_code": 'USD',
#                      "currency_name": 'US Dollar'},]

# df = pd.DataFrame(data=dim_currency_dict)
# query = "INSERT INTO dim_currency VALUES "
# for i, row in df.iterrows():
#     print(tuple(row.values))
#   row[j] for j in range(len(row)))
# print(df)
# df.to_parquet('currency.parquet', index=False)



# df = wr.s3.read_parquet(path=f"s3://blackwater-processed-zone/original_data_dump/dim_staff.parquet")
# print(len(df))
# output_list = ''
# for _, row in df.iterrows():
#     output_list += f"{tuple(row.values)};"
# # print(df[df['design_name'].str.contains('"')])

# output = output_list.replace("<NA>", "null").replace("'s", "s").replace('"', "'")
# pp(output.split(';'))


output = """INSERT INTO dim_design VALUES (8, 'Wooden', '/usr', 'wooden-20220717-npgz.json'), (51, 'Bronze', '/private', 'bronze-20221024-4dds.json'), (50, 'Granite', '/private/var', 'granite-20220205-3vfw.json'), (69, 'Bronze', '/lost+found', 'bronze-20230102-r904.json'), (16, 'Soft', '/System', soft-20211001-cjaz.json'), (54, 'Plastic', '/usr/ports', 'plastic-20221206-bw3l.json'), (55, 'Concrete', '/opt/include', 'concrete-20210614-04nd.json'), (10, 'Soft', '/usr/share', soft-20220201-hzz1.json'), (57, 'Cotton', '/etc/periodic', 'cotton-20220527-vn4b.json'), (41, 'Granite', '/usr/X11R6', 'granite-20220125-ifwa.json'), (45, 'Frozen', '/Users', 'frozen-20221021-bjqs.json'), (2, 'Steel', '/etc/periodic', steel-20210725-fcxq.json'), (4, 'Granite', '/usr/local/src', 'granite-20220430-l5fs.json'), (24, 'Granite', '/etc/mail', 'granite-20210516-8b7j.json'), (30, 'Cotton', '/etc', 'cotton-20220507-r5ui.json'), (31, 'Soft', '/root', soft-20221103-i6wm.json'), (33, 'Steel', '/media', steel-20220201-shjp.json'), (35, 'Wooden', '/usr/share', 'wooden-20211125-6y56.json'), (36, 'Fresh', '/usr/sbin', 'fresh-20221213-fhsy.json'), (12, 'Frozen', '/private/tmp', 'frozen-20201124-fsdu.json'), (39, 'Granite', '/net', 'granite-20220831-q5ev.json'), (15, 'Steel', '/var/log', steel-20210707-zhuw.json'), (40, 'Metal', '/lost+found', 'metal-20221004-53ba.json'), (66, 'Metal', '/rescue', 'metal-20220712-rp0w.json'), (42, 'Metal', '/var/yp', 'metal-20220529-ke0x.json'), (21, 'Wooden', '/opt/lib', 'wooden-20211225-adqt.json'), (46, 'Granite', '/var/tmp', 'granite-20210528-5n3g.json'), (20, 'Metal', '/home', 'metal-20201229-s60u.json'), (62, 'Granite', '/etc/ppp', 'granite-20211004-j4iv.json'), (29, 'Bronze', '/lib', 'bronze-20210307-o8yd.json'), (56, 'Steel', '/usr/libdata', steel-20210123-65zd.json'), (3, 'Steel', '/System', steel-20210621-13gb.json'), (7, 'Wooden', '/System', 'wooden-20211114-otpq.json'), (59, 'Cotton', '/usr/bin', 'cotton-20210901-bgz0.json'), (18, 'Bronze', '/rescue', 'bronze-20210303-f74o.json'), (47, 'Steel', '/Users', steel-20210910-skxr.json'), (64, 'Plastic', '/usr/X11R6', 'plastic-20220312-0d0w.json'), (67, 'Cotton', '/usr/share', 'cotton-20220212-yxcz.json'), (65, 'Frozen', '/private', 'frozen-20210506-52tz.json'), (60, 'Fresh', '/usr', 'fresh-20211212-anbo.json'), (25, 'Bronze', '/usr/libexec', 'bronze-20211128-w9ae.json'), (71, 'Bronze', '/usr', 'bronze-20211101-nx5c.json'), (53, 'Bronze', '/opt/lib', 'bronze-20221012-a8mw.json'), (48, 'Wooden', '/opt/share', 'wooden-20220311-xzey.json'), (77, 'Bronze', '/Applications', 'bronze-20220413-hku5.json'), (63, 'Fresh', '/etc', 'fresh-20220123-y982.json'), (27, 'Concrete', '/net', 'concrete-20220508-l474.json'), (75, 'Frozen', '/usr/libexec', 'frozen-20221126-uhaz.json'), (44, 'Steel', '/boot', steel-20220628-dqrw.json'), (79, 'Cotton', '/usr/libdata', 'cotton-20230204-8wx0.json'), (22, 'Fresh', '/opt', 'fresh-20210615-opko.json'), (80, 'Rubber', '/selinux', 'rubber-20220421-8qca.json'), (81, 'Plastic', '/sbin', 'plastic-20221224-cpuv.json'), (82, 'Bronze', '/home', 'bronze-20220618-25np.json'), (6, 'Fresh', '/opt/sbin', 'fresh-20220807-6ycu.json'), (61, 'Cotton', '/dev', 'cotton-20220616-8nc6.json'), (13, 'Granite', '/home/user/dir', 'granite-20220705-4y7t.json'), (26, 'Rubber', '/etc/periodic', 'rubber-20220814-o6dm.json'), (52, 'Bronze', '/etc/namedb', 'bronze-20210909-ghv2.json'), (78, 'Fresh', '/etc', 'fresh-20210425-bbsy.json'), (9, 'Concrete', '/private/var', 'concrete-20211012-auw9.json'), (32, 'Plastic', '/private/var', 'plastic-20210324-jxeq.json'), (19, 'Frozen', '/lost+found', 'frozen-20210815-rl8i.json'), (49, 'Bronze', '/usr/lib', 'bronze-20220422-3ly6.json'), (23, 'Soft', '/var/log', soft-20210907-yf4z.json'), (68, 'Concrete', '/home/user', 'concrete-20210929-235v.json'), (11, 'Cotton', '/net', 'cotton-20211005-yxjd.json'), (73, 'Granite', '/usr/share', 'granite-20221221-ro5o.json'), (1, 'Wooden', '/lib', 'wooden-20201128-jdvi.json'), (34, 'Wooden', '/usr/local/bin', 'wooden-20211101-2wja.json'), (28, 'Bronze', '/etc', 'bronze-20210303-d7r1.json'), (58, 'Soft', '/net', soft-20220713-5yjr.json'), (43, 'Plastic', '/mnt', 'plastic-20220327-9enf.json'), (5, 'Granite', '/Network', 'granite-20220419-b6n4.json'), (70, 'Cotton', '/home/user/dir', 'cotton-20220124-9xol.json'), (14, 'Granite', '/usr/obj', 'granite-20210406-uwqg.json'), (38, 'Soft', '/System', soft-20210917-8ej0.json'), (37, 'Frozen', '/etc/namedb', 'frozen-20210909-nxsu.json'), (76, 'Fresh', '/boot/defaults', 'fresh-20220725-ytrh.json'), (17, 'Soft', '/usr/include', soft-20210904-uwsd.json'), (85, 'Fresh', '/net', 'fresh-20230226-7p3x.json'), (86, 'Plastic', '/usr/obj', 'plastic-20211205-bg4r.json'), (87, 'Metal', '/home/user/dir', 'metal-20230212-gb94.json'), (89, 'Concrete', '/usr/bin', 'concrete-20221230-2chq.json'), (90, 'Steel', '/net', steel-20230209-1nfx.json'), (93, 'Frozen', '/opt/lib', 'frozen-20220223-4zsk.json'), (94, 'Soft', '/usr/share', soft-20220425-7vge.json'), (95, 'Soft', '/etc/namedb', soft-20210815-c8lb.json'), (96, 'Soft', '/var/spool', soft-20210925-iz9a.json'), (97, 'Plastic', '/usr', 'plastic-20211226-m4aw.json'), (98, 'Concrete', '/sys', 'concrete-20221208-lo7a.json'), (99, 'Fresh', '/usr/ports', 'fresh-20210508-47n4.json'), (103, 'Wooden', '/opt/include', 'wooden-20210915-yhkv.json'), (104, 'Granite', '/opt/lib', 'granite-20211018-eo1o.json'), (105, 'Fresh', '/var/log', 'fresh-20210707-hfiz.json'), (102, 'Granite', '/System', 'granite-20210604-fjnp.json'), (108, 'Cotton', '/opt/lib', 'cotton-20220215-v0be.json'), (110, 'Frozen', '/opt/sbin', 'frozen-20220811-u7v4.json'), (113, 'Metal', '/usr/libexec', 'metal-20230104-81ah.json'), (115, 'Wooden', '/var/log', 'wooden-20220218-sioz.json'), (116, 'Rubber', '/etc/mail', 'rubber-20220905-7ug5.json'), (118, 'Metal', '/usr/src', 'metal-20221219-gy2p.json'), (120, 'Wooden', '/media', 'wooden-20221118-fy74.json'), (114, 'Frozen', '/Library', 'frozen-20220409-xx0n.json'), (122, 'Bronze', '/dev', 'bronze-20220522-ciu2.json'), (123, 'Soft', '/tmp', soft-20220308-59rv.json'), (126, 'Bronze', '/var/yp', 'bronze-20211208-xkxm.json'), (127, 'Bronze', '/net', 'bronze-20210605-o6eo.json'), (117, 'Plastic', '/etc/mail', 'plastic-20210826-05cx.json'), (129, 'Frozen', '/var', 'frozen-20210826-jmyj.json'), (130, 'Soft', '/usr/ports', soft-20220110-ku7d.json'), (131, 'Bronze', '/usr/obj', 'bronze-20210822-r8jg.json'), (133, 'Soft', '/root', soft-20230204-9epx.json'), (128, 'Steel', '/etc/ppp', steel-20220524-bp6u.json'), (136, 'Wooden', '/root', 'wooden-20210803-ftxe.json'), (147, 'Fresh', '/opt/lib', 'fresh-20210629-bdz8.json'), (137, 'Granite', '/Users', 'granite-20220515-ut6f.json'), (138, 'Steel', '/var/log', steel-20220810-qfe8.json'), (140, 'Plastic', '/opt/lib', 'plastic-20210708-oxwg.json'), (142, 'Steel', '/dev', steel-20220403-f7zn.json'), (132, 'Wooden', '/usr/lib', 'wooden-20210716-efid.json'), (144, 'Frozen', '/Applications', 'frozen-20220202-xj5a.json'), (146, 'Metal', '/opt/include', 'metal-20211003-pqut.json'), (148, 'Soft', '/usr/sbin', soft-20211031-r8ls.json'), (149, 'Concrete', '/sys', 'concrete-20211206-42cj.json'), (72, 'Granite', '/etc/periodic', 'granite-20211018-8105.json'), (156, 'Plastic', '/etc/periodic', 'plastic-20221227-yh2k.json'), (157, 'Metal', '/System', 'metal-20211011-vn19.json'), (159, 'Concrete', '/bin', 'concrete-20230515-hz70.json'), (161, 'Concrete', '/selinux', 'concrete-20211003-8qf1.json'), (141, 'Metal', '/sbin', 'metal-20220620-3qt5.json'), (162, 'Rubber', '/opt', 'rubber-20221111-2g9s.json'), (163, 'Plastic', '/lib', 'plastic-20220630-m2sx.json'), (101, 'Granite', '/Users', 'granite-20211224-9u2x.json'), (158, 'Frozen', '/System', 'frozen-20210804-24dq.json'), (145, 'Fresh', '/sbin', 'fresh-20220908-nejm.json'), (139, 'Wooden', '/boot/defaults', 'wooden-20211028-8e7p.json'), (119, 'Fresh', '/bin', 'fresh-20220329-sq22.json'), (154, 'Steel', '/usr/local/src', steel-20210722-6cs3.json'), (100, 'Rubber', '/bin', 'rubber-20220922-qyh9.json'), (106, 'Concrete', '/home/user/dir', 'concrete-20230204-jsls.json'), (84, 'Cotton', '/private', 'cotton-20221215-qgb4.json'), (150, 'Rubber', '/Network', 'rubber-20220216-6lqz.json'), (74, 'Steel', '/etc/defaults', steel-20210918-u2of.json'), (152, 'Cotton', '/opt/sbin', 'cotton-20230414-ca1r.json'), (107, 'Cotton', '/home/user', 'cotton-20220311-2ouk.json'), (124, 'Steel', '/proc', steel-20211017-ye3d.json'), (83, 'Frozen', '/mnt', 'frozen-20210527-z7mi.json'), (92, 'Soft', '/home/user/dir', soft-20221011-kqhw.json'), (153, 'Rubber', '/bin', 'rubber-20210819-z68w.json'), (121, 'Rubber', '/selinux', 'rubber-20220129-pxme.json'), (88, 'Bronze', '/usr/lib', 'bronze-20211230-5u6g.json'), (155, 'Metal', '/opt/lib', 'metal-20230228-wa21.json'), (134, 'Concrete', '/proc', 'concrete-20210809-7v5y.json'), (112, 'Cotton', '/selinux', 'cotton-20220621-k1hx.json'), (109, 'Rubber', '/usr/share', 'rubber-20220705-kkib.json'), (135, 'Cotton', '/usr/libexec', 'cotton-20210622-ktx8.json'), (91, 'Bronze', '/sbin', 'bronze-20220402-mm8l.json'), (111, 'Plastic', '/srv', 'plastic-20220907-h15e.json'), (151, 'Metal', '/bin', 'metal-20220825-4lso.json'), (143, 'Rubber', '/tmp', 'rubber-20220213-inka.json'), (160, 'Steel', '/usr/local/bin', steel-20220811-rn9u.json'), (164, 'Cotton', '/etc', 'cotton-20220728-2rm8.json'), (166, 'Granite', '/opt/bin', 'granite-20211218-2uj7.json'), (167, 'Frozen', '/selinux', 'frozen-20220929-xo6g.json'), (168, 'Bronze', '/boot/defaults', 'bronze-20220314-ocoo.json'), (169, 'Frozen', '/selinux', 'frozen-20220909-chdu.json'), (170, 'Granite', '/Applications', 'granite-20221022-1wfm.json'), (171, 'Plastic', '/usr', 'plastic-20220316-dn2a.json'), (165, 'Granite', '/opt/include', 'granite-20211013-sk3j.json'), (173, 'Soft', '/mnt', soft-20220721-v4jl.json'), (175, 'Rubber', '/opt/bin', 'rubber-20220911-wl13.json'), (178, 'Granite', '/home/user', 'granite-20230213-jtdo.json'), (179, 'Fresh', '/etc/defaults', 'fresh-20230712-odco.json'), (180, 'Soft', '/usr/ports', soft-20220115-m6dl.json'), (181, 'Granite', '/usr/include', 'granite-20230402-fm1k.json'), (182, 'Rubber', '/usr/X11R6', 'rubber-20220531-cxcj.json'), (183, 'Plastic', '/var/yp', 'plastic-20230222-ogev.json'), (184, 'Frozen', '/var', 'frozen-20230513-v3xy.json'), (185, 'Soft', '/var/mail', soft-20220408-1vkx.json'), (177, 'Bronze', '/usr/include', 'bronze-20230211-72k2.json'), (189, 'Cotton', '/etc/namedb', 'cotton-20210929-nvvm.json'), (174, 'Plastic', '/var/tmp', 'plastic-20220408-g5ei.json'), (190, 'Steel', '/usr/libdata', steel-20230522-9l5i.json'), (218, 'Bronze', '/usr/sbin', 'bronze-20221007-najo.json'), (193, 'Frozen', '/etc/periodic', 'frozen-20210826-awdx.json'), (194, 'Cotton', '/usr/libexec', 'cotton-20230111-bcst.json'), (195, 'Soft', '/sys', soft-20220507-mul5.json'), (196, 'Soft', '/usr/X11R6', soft-20210907-shxs.json'), (197, 'Soft', '/private', soft-20230724-fhzz.json'), (198, 'Frozen', '/Users', 'frozen-20220507-s5bg.json'), (199, 'Rubber', '/bin', 'rubber-20220930-btxf.json'), (200, 'Granite', '/lib', 'granite-20220711-4p81.json'), (201, 'Steel', '/private/var', steel-20221101-ib3u.json'), (202, 'Granite', '/home/user/dir', 'granite-20220318-aqwx.json'), (203, 'Frozen', '/var/spool', 'frozen-20220623-oh2p.json'), (191, 'Soft', '/var/spool', soft-20211120-oaid.json'), (204, 'Wooden', '/usr/libexec', 'wooden-20210919-wxr7.json'), (206, 'Soft', '/usr/lib', soft-20221208-eogu.json'), (207, 'Bronze', '/sys', 'bronze-20221021-31bh.json'), (208, 'Plastic', '/usr/share', 'plastic-20230823-prpf.json'), (209, 'Wooden', '/usr/share', 'wooden-20230306-7t9t.json'), (210, 'Cotton', '/usr/share', 'cotton-20211224-2tud.json'), (211, 'Soft', '/bin', soft-20230718-idjt.json'), (212, 'Plastic', '/etc/ppp', 'plastic-20220815-blc6.json'), (214, 'Plastic', '/var', 'plastic-20211220-4s5b.json'), (215, 'Bronze', '/etc/namedb', 'bronze-20230316-x1sb.json'), (216, 'Concrete', '/usr/share', 'concrete-20220514-yusd.json'), (219, 'Bronze', '/usr/ports', 'bronze-20230317-l7kd.json'), (220, 'Concrete', '/boot', 'concrete-20230517-k8kg.json'), (187, 'Bronze', '/boot', 'bronze-20230625-lojh.json'), (221, 'Granite', '/usr/lib', 'granite-20220107-q0ot.json'), (222, 'Plastic', '/etc/namedb', 'plastic-20220227-59dm.json'), (223, 'Plastic', '/home/user/dir', 'plastic-20220831-7i7d.json'), (224, 'Soft', '/usr/bin', soft-20220614-1sgl.json'), (225, 'Soft', '/usr/bin', soft-20220929-k18k.json'), (226, 'Steel', '/Library', steel-20230311-iys7.json'), (227, 'Frozen', '/etc/mail', 'frozen-20220311-zjib.json'), (229, 'Soft', '/lib', soft-20220102-7g8f.json'), (230, 'Steel', '/Library', steel-20230526-3oih.json'), (231, 'Steel', '/etc/mail', steel-20230221-jyus.json'), (217, 'Cotton', '/private/tmp', 'cotton-20230522-60b7.json'), (232, 'Frozen', '/etc/defaults', 'frozen-20231002-9s98.json'), (233, 'Frozen', '/Users', 'frozen-20221202-dhdd.json'), (234, 'Steel', '/etc/namedb', steel-20220313-97g7.json'), (235, 'Plastic', '/usr/local/src', 'plastic-20230930-0p4v.json'), (236, 'Cotton', '/private/tmp', 'cotton-20220916-tuoi.json'), (237, 'Concrete', '/net', 'concrete-20220511-y217.json'), (238, 'Soft', '/srv', soft-20230522-jeud.json'), (240, 'Fresh', '/usr/src', 'fresh-20220126-nv96.json'), (242, 'Concrete', '/usr/ports', 'concrete-20230930-rklw.json'), (243, 'Concrete', '/usr', 'concrete-20220827-nfpt.json'), (244, 'Steel', '/boot/defaults', steel-20211202-nbf0.json'), (245, 'Concrete', '/selinux', 'concrete-20231009-f727.json'), (241, 'Rubber', '/usr/obj', 'rubber-20230319-mate.json'), (205, 'Frozen', '/rescue', 'frozen-20230722-ddu4.json'), (192, 'Concrete', '/sys', 'concrete-20210823-c0jp.json'), (172, 'Steel', '/private/tmp', steel-20230116-uwp6.json'), (176, 'Concrete', '/var/tmp', 'concrete-20220406-h9s7.json'), (188, 'Rubber', '/Library', 'rubber-20221203-59l5.json'), (213, 'Frozen', '/usr', 'frozen-20220819-8bv5.json'), (239, 'Soft', '/usr/X11R6', soft-20231007-xdso.json'), (228, 'Bronze', '/var', 'bronze-20230819-tn98.json'), (246, 'Plastic', '/lost+found', 'plastic-20230608-7h1o.json'), (247, 'Soft', '/etc', soft-20221208-pa0r.json'), (248, 'Fresh', '/usr/libdata', 'fresh-20220421-r599.json'), (249, 'Soft', '/usr/ports', soft-20220325-kyoj.json'), (250, 'Bronze', '/usr/share', 'bronze-20211202-gc4f.json'), (253, 'Metal', '/net', 'metal-20230629-2un5.json'), (186, 'Metal', '/var/tmp', 'metal-20230530-n86x.json'), (254, 'Granite', '/dev', 'granite-20220708-hnle.json'), (255, 'Steel', '/opt/lib', steel-20230429-28vi.json'), (257, 'Steel', '/System', steel-20220705-frap.json'), (258, 'Frozen', '/home/user/dir', 'frozen-20220630-vsnx.json'), (259, 'Bronze', '/usr/include', 'bronze-20211219-cxlb.json'), (261, 'Granite', '/opt', 'granite-20220609-92sv.json'), (262, 'Fresh', '/rescue', 'fresh-20220809-zhoc.json'), (264, 'Wooden', '/opt/bin', 'wooden-20230615-s2u0.json'), (265, 'Metal', '/root', 'metal-20230204-yxyp.json'), (266, 'Steel', '/usr/sbin', steel-20220603-3zkh.json'), (268, 'Cotton', '/usr/libexec', 'cotton-20220504-wk9z.json'), (270, 'Steel', '/sbin', steel-20220218-0qvw.json'), (271, 'Cotton', '/opt/sbin', 'cotton-20231216-hudw.json'), (125, 'Bronze', '/usr/sbin', 'bronze-20221021-ogju.json'), (272, 'Bronze', '/usr/bin', 'bronze-20220612-rl71.json'), (273, 'Soft', '/usr/libdata', soft-20221205-a6p6.json'), (274, 'Concrete', '/usr/share', 'concrete-20230830-8tuw.json'), (275, 'Metal', '/etc', 'metal-20231005-9zhu.json'), (276, 'Frozen', '/usr/libexec', 'frozen-20230922-e3mz.json'), (277, 'Metal', '/etc/periodic', 'metal-20220408-5pcq.json'), (267, 'Steel', '/home/user/dir', steel-20220615-cjs8.json'), (278, 'Bronze', '/usr/sbin', 'bronze-20230707-kqlf.json'), (279, 'Wooden', '/usr/libexec', 'wooden-20220317-54qi.json'), (281, 'Frozen', '/opt/lib', 'frozen-20221115-scdl.json'), (282, 'Concrete', '/var', 'concrete-20230604-gg3c.json'), (283, 'Steel', '/usr/X11R6', steel-20230724-pj7l.json'), (284, 'Fresh', '/lost+found', 'fresh-20231024-g1ig.json'), (285, 'Frozen', '/etc/defaults', 'frozen-20230815-zije.json'), (252, 'Bronze', '/proc', 'bronze-20220717-lauo.json'), (287, 'Granite', '/sys', 'granite-20231221-9ds9.json'), (288, 'Plastic', '/selinux', 'plastic-20230415-fcnk.json'), (289, 'Fresh', '/etc/mail', 'fresh-20220522-llpr.json'), (290, 'Bronze', '/etc/defaults', 'bronze-20220906-5ud8.json'), (291, 'Plastic', '/opt/include', 'plastic-20221005-a2tj.json'), (256, 'Rubber', '/usr/obj', 'rubber-20221210-zgjo.json'), (292, 'Fresh', '/tmp', 'fresh-20221004-wp56.json'), (293, 'Concrete', '/opt/lib', 'concrete-20230525-vjxp.json'), (294, 'Steel', '/usr/libdata', steel-20231215-tsg6.json'), (295, 'Granite', '/opt/bin', 'granite-20231104-zwfn.json'), (296, 'Cotton', '/var/tmp', 'cotton-20231027-wsml.json'), (297, 'Granite', '/var/yp', 'granite-20220702-2ql0.json'), (298, 'Rubber', '/etc/periodic', 'rubber-20230713-0nw3.json'), (299, 'Wooden', '/root', 'wooden-20220321-6rsd.json'), (300, 'Soft', '/sbin', soft-20220715-syjh.json'), (301, 'Frozen', '/etc/mail', 'frozen-20230614-n2b7.json'), (302, 'Bronze', '/private', 'bronze-20230409-5hxv.json'), (303, 'Rubber', '/usr', 'rubber-20230910-9pd4.json'), (304, 'Steel', '/Library', steel-20220619-ec5y.json'), (305, 'Plastic', '/Applications', 'plastic-20230331-y8yc.json'), (306, 'Bronze', '/Library', 'bronze-20220516-wtp0.json'), (307, 'Soft', '/opt', soft-20230511-iz8m.json'), (309, 'Metal', '/usr/libdata', 'metal-20230313-dkd3.json'), (286, 'Steel', '/lib', steel-20230607-smh9.json'), (310, 'Wooden', '/System', 'wooden-20220626-xhic.json'), (311, 'Steel', '/lost+found', steel-20220407-1se7.json'), (312, 'Concrete', '/lib', 'concrete-20220529-7tii.json'), (313, 'Plastic', '/Users', 'plastic-20231231-fsdr.json'), (314, 'Cotton', '/usr/src', 'cotton-20220926-rgqy.json'), (315, 'Concrete', '/System', 'concrete-20230717-u6p2.json'), (317, 'Wooden', '/private/var', 'wooden-20230710-hxsv.json'), (318, 'Cotton', '/boot/defaults', 'cotton-20230518-lql8.json'), (319, 'Concrete', '/etc', 'concrete-20220904-tsq7.json'), (320, 'Granite', '/usr/local/src', 'granite-20230421-evia.json'), (321, 'Plastic', '/net', 'plastic-20230801-8l45.json'), (322, 'Soft', '/Network', soft-20220610-w39k.json'), (323, 'Plastic', '/net', 'plastic-20230613-0smf.json'), (324, 'Wooden', '/private', 'wooden-20230507-4qfk.json'), (325, 'Rubber', '/mnt', 'rubber-20230331-e38p.json'), (326, 'Wooden', '/etc', 'wooden-20220904-5xaa.json'), (251, 'Wooden', '/var/log', 'wooden-20230413-ofsb.json'), (308, 'Concrete', '/usr/src', 'concrete-20220913-ipsg.json'), (260, 'Cotton', '/usr/libexec', 'cotton-20231002-xhpz.json'), (280, 'Rubber', '/lost+found', 'rubber-20231020-ol28.json'), (269, 'Plastic', '/root', 'plastic-20221024-ss3c.json'), (316, 'Fresh', '/net', 'fresh-20230213-1kvk.json'), (327, 'Steel', '/selinux', steel-20230427-9vsa.json'), (263, 'Wooden', '/Network', 'wooden-20220317-9viu.json'), (328, 'Wooden', '/opt', 'wooden-20221021-zwq8.json'), (329, 'Soft', '/usr/lib', soft-20220629-yv4w.json'), (330, 'Concrete', '/etc/periodic', 'concrete-20230608-0j9i.json'), (331, 'Frozen', '/usr/obj', 'frozen-20230329-5fut.json'), (332, 'Cotton', '/etc/periodic', 'cotton-20230412-tf84.json'), (333, 'Fresh', '/net', 'fresh-20230127-9h9f.json'), (334, 'Concrete', '/var/tmp', 'concrete-20240217-2zxa.json'), (335, 'Frozen', '/usr/libexec', 'frozen-20230118-qls7.json'), (336, 'Soft', '/var/tmp', soft-20221207-wley.json'), (337, 'Concrete', '/usr/local/bin', 'concrete-20240227-i0cs.json'), (338, 'Rubber', '/etc/periodic', 'rubber-20240127-poeh.json'), (340, 'Concrete', '/boot/defaults', 'concrete-20230604-zuyt.json'), (341, 'Granite', '/selinux', 'granite-20221030-p1fg.json'), (342, 'Cotton', '/lib', 'cotton-20220418-m6hn.json'), (343, 'Frozen', '/var/log', 'frozen-20221031-6jq5.json'), (344, 'Cotton', '/net', 'cotton-20230725-dux8.json'), (345, 'Soft', '/etc/periodic', soft-20220918-5fvo.json'), (346, 'Granite', '/usr/include', 'granite-20230227-wzwi.json'), (347, 'Bronze', '/boot', 'bronze-20230625-3agx.json'), (348, 'Concrete', '/usr/ports', 'concrete-20220729-9bx3.json'), (349, 'Granite', '/usr', 'granite-20230215-cpyi.json'), (350, 'Concrete', '/usr/local/src', 'concrete-20230108-8th1.json'), (339, 'Metal', '/usr', 'metal-20220426-6eg5.json'), (351, 'Granite', '/var/tmp', 'granite-20220622-mv79.json'), (352, 'Cotton', '/net', 'cotton-20220913-glod.json'), (353, 'Metal', '/private/tmp', 'metal-20230622-ggr1.json'), (354, 'Steel', '/usr/obj', steel-20230624-nil0.json'), (355, 'Frozen', '/home/user', 'frozen-20221101-p7d7.json'), (356, 'Plastic', '/lib', 'plastic-20231126-npry.json'), (357, 'Metal', '/dev', 'metal-20240415-ren8.json'), (358, 'Plastic', '/Applications', 'plastic-20221221-c3d8.json'), (359, 'Metal', '/usr/local/bin', 'metal-20231212-ersj.json'), (360, 'Steel', '/home', steel-20230111-mwuw.json'), (362, 'Rubber', '/srv', 'rubber-20230323-ez7e.json'), (361, 'Metal', '/private', 'metal-20230913-np2p.json'), (363, 'Frozen', '/mnt', 'frozen-20231220-scc9.json'), (364, 'Soft', '/usr/sbin', soft-20230604-gszc.json'), (365, 'Metal', '/srv', 'metal-20230502-v9gc.json'), (366, 'Bronze', '/opt/include', 'bronze-20220512-u9v0.json'), (367, 'Granite', '/opt', 'granite-20230416-kg1t.json'), (368, 'Rubber', '/dev', 'rubber-20220729-f8kx.json'), (369, 'Concrete', '/etc/namedb', 'concrete-20220717-fxwc.json'), (370, 'Frozen', '/usr/include', 'frozen-20230202-zd3g.json'), (371, 'Frozen', '/etc/namedb', 'frozen-20230907-4z1n.json'), (372, 'Plastic', '/usr/local/src', 'plastic-20230623-8inm.json'), (373, 'Fresh', '/var/log', 'fresh-20231016-4k7b.json'), (374, 'Bronze', '/var/yp', 'bronze-20221206-wm5q.json'), (375, 'Soft', '/usr/X11R6', soft-20230424-ll2o.json'), (376, 'Concrete', '/usr/share', 'concrete-20240508-p1ln.json'), (377, 'Cotton', '/lib', 'cotton-20230829-i2w7.json'), (378, 'Granite', '/opt', 'granite-20240512-6307.json'), (379, 'Frozen', '/usr/lib', 'frozen-20220814-mktj.json'), (380, 'Fresh', '/var/spool', 'fresh-20240519-x7w4.json') RETURNING *;"""

print(output[300:320])
