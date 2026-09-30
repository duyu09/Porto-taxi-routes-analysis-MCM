# Travel Pattern Recognition and Dynamic Route Optimization Based on Taxi Trajectory Data

## Documentation Language

[**繁體中文**](./README.md) | [**English**](./README.en.md) | [**Tiếng Việt**](./README.vi.md)

> The following text was translated using the GPT-5.6 model and has been manually reviewed. However, errors may still occur. In case of any ambiguity or discrepancy, please refer to the Traditional Chinese version as the authoritative version.

## Overview

This project investigates taxi trajectories in Porto, Portugal, with the aim of identifying travel patterns from vehicle movements and incorporating urban demand and road traffic conditions into route planning. Through interpretable statistical modeling, the study characterizes urban travel demand and road operating conditions, and explores route choices under different objectives from the perspectives of passenger travel efficiency and drivers’ potential passenger-pickup opportunities. The research follows the sequence of “**trajectory description → pattern recognition → demand analysis → route optimization**”: first, discrete positioning points are transformed into analyzable trip descriptions; then, the travel characteristics associated with different passenger-pickup modes are identified; next, the temporal and spatial distributions of demand are characterized; finally, route choice models are established from the perspectives of passengers and drivers.

**Keywords:** Travel Pattern Recognition｜Urban Demand Analysis｜Dynamic Route Optimization

📄 [**Read the Full Competition Paper Here**](202602077-完整论文.pdf)

## Repository Structure

```text
.
├── README.md
├── LICENSE
├── 202602077-完整论文.pdf     # Competition paper
├── ds_code/                  # Modeling code
├── outputs/                  # Analysis outputs
└── images/                   # Paper and project figures
```

## Research Framework

Taxi trajectory data simultaneously contain information at three levels: trips, demand, and the road network:

- **Trip level:** how a trip occurs, how long it lasts, and how the vehicle moves along the route.
- **Demand level:** where trips originate, where they are directed, and how they vary across different time periods.
- **Road-network level:** which roads vehicles travel through, and what traffic conditions and passenger-pickup opportunities characterize those roads.

These three levels are interconnected. Trip descriptions provide the basis for pattern recognition, origin–destination distributions form the structure of urban demand, and historical road operating information supports the construction of route costs.

<img src="./images/Fig01.svg" style="width:60%" />

*Research workflow extending from trajectory analysis to travel pattern recognition and route optimization.*

## Trajectory Description and Travel Pattern Recognition

### From Positioning Points to Trip Descriptions

A raw trajectory is a sequence of positioning points ordered by time. To analyze travel behavior, these points need to be transformed into trip descriptions with explicit meanings, such as travel distance, duration, average speed, and route geometry.

Suppose a trajectory contains $n$ positioning points, with a sampling interval of $\Delta t$ between adjacent points, and let $d_H$ denote the spherical distance. Then the trip duration and cumulative distance can be expressed as:

$$D=(n-1)\Delta t,\qquad L=\sum_{j=1}^{n-1}d_H(p_j,p_{j+1}),\qquad V=\frac{L}{D}.$$

Distance and time describe the scale of a trip, while route geometry provides additional information about differences in movement patterns. For example, the same origin and destination may correspond to different degrees of detouring; similarly, trips with comparable distances may have different travel times because of road conditions. Therefore, travel behavior needs to be described jointly from multiple perspectives.

### Probabilistic Recognition of Travel Patterns

This study treats telephone-dispatched trips, taxi-stand pickups, and street-hail pickups as different travel patterns. The core of the recognition problem is to use the temporal, spatial, and movement characteristics of a trip to estimate the probability that it belongs to each pattern.

Let $x$ denote the trip description and $f_k(x)$ the model score for the $k$-th pattern. The scores can be converted into probabilities using Softmax:

$$\Pr(y=k\mid x)=\frac{\exp(f_k(x))}{\sum_{\ell=1}^{K}\exp(f_\ell(x))},\qquad \hat y=\arg\max_{1\leq k\leq K}\Pr(y=k\mid x).$$

This modeling approach allows multiple types of information to jointly influence the classification and can also capture nonlinear relationships. For example, time and location may jointly affect the passenger-pickup mode, and examining either factor alone is insufficient to explain the complete travel pattern.

### Model Interpretation

Travel pattern recognition should not only answer “which category does this trip belong to?” but also explain “which information influenced the prediction?” This study adopts the additive explanation framework of SHAP, decomposing a prediction into a baseline output and the contributions of individual features:

$$f(x)=\phi_0+\sum_{j=1}^{m}\phi_j.$$

Here, $\phi_0$ denotes the baseline output, while $\phi_j$ represents the contribution of the $j$-th feature to the prediction. This decomposition helps explain how the model integrates different types of information. However, it reveals statistical relationships within the model and should not be interpreted directly as evidence of causal relationships.

## Spatiotemporal Structure of Urban Demand

### OD Flows

Connections between origins and destinations form origin–destination (OD) relationships. By dividing the study area into spatial units and aggregating trips by time period, time-specific OD matrices can be constructed:

$$F_{ab}^{(r)}=\sum_{i=1}^{N}\mathbf{1}\{g_i^o=a,\ g_i^d=b,\ t_i\in r\}.$$

Here, $F_{ab}^{(r)}$ denotes the number of trips from area $a$ to area $b$ during time period $r$, while $g_i^o$ and $g_i^d$ denote the origin and destination areas of the $i$-th trip, respectively.

The OD matrix preserves both the locations and directions of travel demand. It can therefore describe connections between areas while also allowing comparisons of how these connections change across different time periods.

### Pickup and Drop-off Hotspots

By summing the OD matrix along the destination and origin dimensions, respectively, the departure and arrival volumes of each area can be obtained:

$$O_a^{(r)}=\sum_bF_{ab}^{(r)},\qquad M_b^{(r)}=\sum_aF_{ab}^{(r)}.$$

Departure volume characterizes the concentration of passenger-pickup demand, while arrival volume reflects the attractiveness of destinations. The two have different interpretations: a large number of trips arriving in an area does not necessarily mean that the area simultaneously has high passenger-pickup demand.

Analysis by time period further preserves temporal differences in demand, enabling subsequent route planning to account for the demand environment associated with the departure time.

## Road Conditions and Demand Opportunities

Route planning requires trip-level information to be transformed into road-level descriptions. After matching trajectories to the road network, road travel times, congestion levels, and passenger-pickup opportunities can be estimated for different time periods.

### Congestion Level

Road congestion can be described by the ratio between historical travel time and free-flow travel time:

$$q_e^{(r)}=\frac{\tau_e^{(r)}}{\tau_e^0+\varepsilon}.$$

Here, $\tau_e^{(r)}$ denotes the historically estimated travel time of road $e$ during time period $r$, $\tau_e^0$ denotes the free-flow travel time, and $\varepsilon$ is a small positive value used to avoid numerical problems.

This ratio describes the travel delay of a road relative to free-flow conditions, allowing route selection to account for operational differences among roads and across time periods.

<img src="./images/Fig05.svg" style="width:75%" />

*Spatial representation of road congestion levels*

### Passenger-Pickup Opportunities

Passenger-pickup opportunities near a road can be approximated by the ratio between the historical number of pickup events and the number of visits to that road:

$$p_e^{+(r)}=\frac{N_{e,+}^{(r)}}{N_e^{(r)}+\varepsilon}.$$

Here, $N_{e,+}^{(r)}$ denotes the number of passenger pickups originating near road $e$, while $N_e^{(r)}$ denotes the historical number of visits to that road.

This indicator provides demand-related information for drivers’ route choices. Since the amount of historical observation data affects estimation stability, passenger-pickup opportunities need to be considered jointly with travel costs.

<img src="./images/Fig06.svg" style="width:75%" />

*Spatial representation of passenger-pickup opportunities on roads*

## Dual-Perspective Dynamic Route Optimization

### Passenger Perspective

From the passenger perspective, route selection primarily focuses on the travel cost required to reach the destination. Distance, travel time, congestion, and road risk jointly affect the travel experience. Therefore, different factors need to be transformed into comparable scales before being combined into road costs.

This composite cost allows route selection to balance multiple objectives. For example, a shorter road segment may have a higher congestion cost, whereas a moderate detour may improve overall travel efficiency.

### Driver Perspective

In addition to travel costs, drivers are also concerned with potential passenger-pickup opportunities along the route. Therefore, road evaluation from the driver perspective needs to consider both travel costs and potential demand benefits.

Roads with higher demand may justify a certain amount of additional travel cost, but demand opportunities must also be constrained by distance, travel time, and congestion. Route selection therefore represents a trade-off between travel costs and potential benefits.

### Route Solution

Representing the road network as a graph, let $\mathcal{P}(o,d)$ denote the set of feasible paths from origin $o$ to destination $d$, and let $C_{e,p}^{(r)}$ and $C_{e,d}^{(r)}$ denote the road costs from the passenger and driver perspectives, respectively. The two route-planning problems can then be expressed uniformly as:

$$P_p^*=\arg\min_{P\in\mathcal{P}(o,d)}\sum_{e\in P}C_{e,p}^{(r)},\qquad P_d^*=\arg\min_{P\in\mathcal{P}(o,d)}\sum_{e\in P}C_{e,d}^{(r)}.$$

The two perspectives use the same road network but evaluate the value of each road differently, and may therefore select different routes. Since their objective functions differ, the aggregate cost values under the two perspectives should not be directly compared to determine superiority.

The term “dynamic” here refers to the fact that road costs vary across time periods: the same road segment may have different traffic conditions and demand opportunities at different times, thereby changing the selection of the entire route. This framework is based on historical information divided by time period.

<img src="./images/Fig07.jpg" style="width:60%" />

*Blue indicates the passenger-perspective route, while red indicates the driver-perspective route.*

## Authors and License

For the complete research, please refer to [*Travel Pattern Recognition and Dynamic Route Optimization Based on Taxi Trajectory Data*](202602077-完整论文.pdf). The terms governing the use and redistribution of this project are provided in [`LICENSE`](LICENSE); external datasets and map resources should be used in accordance with their respective licensing terms.

**Copyright &copy; 2026 [何非凡 (HE Feifan; HÀ Phi Phàm)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/xsxx/2554/content/1835.htm)、[杜宇 (DU Yu; ĐỖ Vũ)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/xsxx/2554/content/1837.htm)、閆媛媛 (YAN Yuanyuan; DIÊM Viện Viện)。Supervisor: [陳梅教授 (Prof. CHEN Mei; GS. TRẦN Mai)](https://faculty.lzjtu.edu.cn/chenmei/zh_CN/index/2541/list/index.htm), School of Electronic and Information Engineering, Lanzhou Jiaotong University**